import contextlib
import inspect
import logging
import typing
import warnings
from contextlib import AbstractAsyncContextManager, AbstractContextManager
from contextvars import ContextVar, Token
from functools import wraps
from types import TracebackType

from typing_extensions import TypeIs

from that_depends.entities.resource_context import ResourceContext
from that_depends.meta import BaseContainerMeta
from that_depends.providers.base import AbstractResource


if typing.TYPE_CHECKING:
    from that_depends.container import BaseContainer


logger: typing.Final = logging.getLogger(__name__)
T_co = typing.TypeVar("T_co", covariant=True)
P = typing.ParamSpec("P")
_CONTAINER_CONTEXT: typing.Final[ContextVar[dict[str, typing.Any]]] = ContextVar("CONTAINER_CONTEXT")
AppType = typing.TypeVar("AppType")
Scope = typing.MutableMapping[str, typing.Any]
Message = typing.MutableMapping[str, typing.Any]
Receive = typing.Callable[[], typing.Awaitable[Message]]
Send = typing.Callable[[Message], typing.Awaitable[None]]
ASGIApp = typing.Callable[[Scope, Receive, Send], typing.Awaitable[None]]
_ASYNC_CONTEXT_KEY: typing.Final[str] = "__ASYNC_CONTEXT__"

ContextType = dict[str, typing.Any]


def _get_container_context() -> dict[str, typing.Any]:
    try:
        return _CONTAINER_CONTEXT.get()
    except LookupError as exc:
        msg = "Context is not set. Use container_context"
        raise RuntimeError(msg) from exc


def fetch_context_item(key: str, default: typing.Any = None) -> typing.Any:  # noqa: ANN401
    return _get_container_context().get(key, default)


T = typing.TypeVar("T")


class ContextResource(
    AbstractResource[T_co],
    AbstractAsyncContextManager[ResourceContext[T_co]],
    AbstractContextManager[ResourceContext[T_co]],
):
    __slots__ = (
        "is_async",
        "_creator",
        "_args",
        "_kwargs",
        "_override",
        "_internal_name",
        "_context",
        "_token",
    )

    def __repr__(self) -> str:
        return f"ContextResource({self._creator.__name__})"

    def __init__(
        self,
        creator: typing.Callable[P, typing.Iterator[T_co] | typing.AsyncIterator[T_co]],
        *args: P.args,
        **kwargs: P.kwargs,
    ) -> None:
        super().__init__(creator, *args, **kwargs)
        self._context: ContextVar[ResourceContext[T_co]] = ContextVar(f"{self._creator.__name__}-context")
        self._token: Token[ResourceContext[T_co]] | None = None

    def __enter__(self) -> ResourceContext[T_co]:
        if self.is_async:
            msg = "You must enter async context for async creators."
            raise RuntimeError(msg)
        return self._enter()

    async def __aenter__(self) -> ResourceContext[T_co]:
        return self._enter()

    def _enter(self) -> ResourceContext[T_co]:
        self._token = self._context.set(ResourceContext(is_async=self.is_async))
        return self._context.get()

    def __exit__(
        self, exc_type: type[BaseException] | None, exc_value: BaseException | None, traceback: TracebackType | None
    ) -> None:
        if not self._token:
            msg = "Context is not set, call ``__enter__`` first"
            raise RuntimeError(msg)

        try:
            context_item = self._context.get()
            context_item.sync_tear_down()

        finally:
            self._context.reset(self._token)

    async def __aexit__(
        self, exc_type: type[BaseException] | None, exc_val: BaseException | None, traceback: TracebackType | None
    ) -> None:
        if self._token is None:
            msg = "Context is not set, call ``__aenter__`` first"
            raise RuntimeError(msg)

        try:
            context_item = self._context.get()
            if context_item.is_context_stack_async(context_item.context_stack):
                await context_item.tear_down()
            else:
                context_item.sync_tear_down()
        finally:
            self._context.reset(self._token)

    @contextlib.contextmanager
    def sync_context(self) -> typing.Iterator[ResourceContext[T_co]]:
        if self.is_async:
            msg = "Please use async context instead."
            raise RuntimeError(msg)
        token = self._token
        with self as val:
            yield val
        self._token = token

    @contextlib.asynccontextmanager
    async def async_context(self) -> typing.AsyncIterator[ResourceContext[T_co]]:
        token = self._token
        async with self as val:
            yield val
        self._token = token

    def context(
        self,
    ) -> typing.Callable[[typing.Callable[P, T]], typing.Callable[P, T]]:
        """Create a new context manager for the resource, the context manager will be async if the resource is async.

        :return: A context manager for the resource.
        :rtype: typing.ContextManager[ResourceContext[T_co]] | typing.AsyncContextManager[ResourceContext[T_co]]
        """
        if self.is_async:
            return typing.cast(typing.Callable[[typing.Callable[P, T]], typing.Callable[P, T]], self.async_context())
        return typing.cast(typing.Callable[[typing.Callable[P, T]], typing.Callable[P, T]], self.sync_context())

    def _fetch_context(self) -> ResourceContext[T_co]:
        try:
            return self._context.get()
        except LookupError as e:
            msg = "Context is not set. Use container_context"
            raise RuntimeError(msg) from e


ContainerType = typing.TypeVar("ContainerType", bound="type[BaseContainer]")


class container_context(AbstractContextManager[ContextType], AbstractAsyncContextManager[ContextType]):  # noqa: N801
    ___slots__ = (
        "_providers",
        "_context_stack",
        "_containers",
        "_initial_context",
        "_context_token",
        "_reset_resource_context",
    )

    def __init__(
        self,
        initial_context: ContextType | None = None,
        providers: list[ContextResource[typing.Any]] | None = None,
        containers: list[ContainerType] | None = None,
        preserve_globals: bool = False,
        reset_resource_context: bool = False,
    ) -> None:
        """Initialize a container context.

        :param initial_context: existing context to use
        :param providers: providers to reset context of.
        :param containers: containers to reset context of.
        :param preserve_globals: whether to preserve global context vars.
        :param reset_resource_context: whether to reset resource context.
        """
        if preserve_globals and initial_context:
            self._initial_context = {**_get_container_context(), **initial_context}
        else:
            self._initial_context: ContextType = _get_container_context() if preserve_globals else initial_context or {}  # type: ignore[no-redef]
        self._context_token: Token[ContextType] | None = None
        self._providers: set[ContextResource[typing.Any]] = set()
        self._reset_resource_context: typing.Final[bool] = (not containers and not providers) or reset_resource_context
        if providers:
            for provider in providers:
                if isinstance(provider, ContextResource):
                    self._providers.add(provider)
                else:
                    msg = "Provider is not a ContextResource"
                    raise TypeError(msg)
        if containers:
            self._add_providers_from_containers(containers)
        if self._reset_resource_context:
            self._add_providers_from_containers(BaseContainerMeta.get_instances())

        self._context_stack: contextlib.AsyncExitStack | contextlib.ExitStack | None = None

    def _add_providers_from_containers(self, containers: list[ContainerType]) -> None:
        for container in containers:
            for container_provider in container.get_providers().values():
                if isinstance(container_provider, ContextResource):
                    self._providers.add(container_provider)

    def __enter__(self) -> ContextType:
        self._context_stack = contextlib.ExitStack()
        for provider in self._providers:
            if self._reset_resource_context:
                if not provider.is_async:
                    self._context_stack.enter_context(provider.sync_context())
            else:
                self._context_stack.enter_context(provider.sync_context())
        return self._enter_globals()

    async def __aenter__(self) -> ContextType:
        self._context_stack = contextlib.AsyncExitStack()
        for provider in self._providers:
            await self._context_stack.enter_async_context(provider.async_context())
        return self._enter_globals()

    def _enter_globals(self) -> ContextType:
        self._context_token = _CONTAINER_CONTEXT.set(self._initial_context)
        return _CONTAINER_CONTEXT.get()

    def _is_context_token(self, _: Token[ContextType] | None) -> TypeIs[Token[ContextType]]:
        return isinstance(_, Token)

    def _exit_globals(self) -> None:
        if self._is_context_token(self._context_token):
            return _CONTAINER_CONTEXT.reset(self._context_token)
        msg = "No context token set for global vars, use __enter__ or __aenter__ first."
        raise RuntimeError(msg)

    def _has_async_exit_stack(
        self,
        _: contextlib.AsyncExitStack | contextlib.ExitStack | None,
    ) -> typing.TypeGuard[contextlib.AsyncExitStack]:
        return isinstance(_, contextlib.AsyncExitStack)

    def _has_sync_exit_stack(
        self, _: contextlib.AsyncExitStack | contextlib.ExitStack | None
    ) -> typing.TypeGuard[contextlib.ExitStack]:
        return isinstance(_, contextlib.ExitStack)

    def __exit__(
        self, exc_type: type[BaseException] | None, exc_value: BaseException | None, traceback: TracebackType | None
    ) -> None:
        try:
            if self._has_sync_exit_stack(self._context_stack):
                self._context_stack.close()
            else:
                msg = "Context is not set, call ``__enter__`` first"
                raise RuntimeError(msg)
        finally:
            self._exit_globals()

    async def __aexit__(
        self, exc_type: type[BaseException] | None, exc_val: BaseException | None, traceback: TracebackType | None
    ) -> None:
        try:
            if self._has_async_exit_stack(self._context_stack):
                await self._context_stack.aclose()
            else:
                msg = "Context is not set, call ``__aenter__`` first"
                raise RuntimeError(msg)
        finally:
            self._exit_globals()

    def __call__(self, func: typing.Callable[P, T_co]) -> typing.Callable[P, T_co]:
        if inspect.iscoroutinefunction(func):

            @wraps(func)
            async def _async_inner(*args: P.args, **kwargs: P.kwargs) -> T_co:
                async with container_context(
                    providers=list(self._providers), reset_resource_context=self._reset_resource_context
                ):
                    return await func(*args, **kwargs)  # type: ignore[no-any-return]

            return typing.cast(typing.Callable[P, T_co], _async_inner)

        @wraps(func)
        def _sync_inner(*args: P.args, **kwargs: P.kwargs) -> T_co:
            with container_context(
                providers=list(self._providers), reset_resource_context=self._reset_resource_context
            ):
                return func(*args, **kwargs)

        return _sync_inner


class AsyncContextResource(ContextResource[T_co]):
    def __init__(
        self,
        creator: typing.Callable[P, typing.AsyncIterator[T_co]],
        *args: P.args,
        **kwargs: P.kwargs,
    ) -> None:
        warnings.warn("AsyncContextResource is deprecated, use ContextResource instead", RuntimeWarning, stacklevel=1)
        super().__init__(creator, *args, **kwargs)


class DIContextMiddleware:
    def __init__(self, app: ASGIApp) -> None:
        self.app: typing.Final = app

    @container_context()
    async def __call__(self, scope: Scope, receive: Receive, send: Send) -> None:
        return await self.app(scope, receive, send)
