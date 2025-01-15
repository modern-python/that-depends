import abc
import asyncio
import contextlib
import inspect
import logging
import typing
from abc import abstractmethod
from contextlib import AbstractAsyncContextManager, AbstractContextManager
from contextvars import ContextVar, Token
from functools import wraps
from types import TracebackType
from typing import Final

from typing_extensions import TypeIs, override

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
CT = typing.TypeVar("CT")


class SupportsContext(typing.Generic[CT], abc.ABC):
    @abstractmethod
    def context(self, func: typing.Callable[P, T]) -> typing.Callable[P, T]:
        """Initialize context for the given function.

        Args:
            func: function to wrap.

        Returns:
            wrapped function with context.

        """

    @abstractmethod
    def async_context(self) -> typing.AsyncContextManager[CT]:
        """Initialize async context."""

    @abstractmethod
    def sync_context(self) -> typing.ContextManager[CT]:
        """Initialize sync context."""

    @abstractmethod
    def supports_sync_context(self) -> bool:
        """Check if the resource supports sync context."""


class ContextResource(
    AbstractResource[T_co],
    SupportsContext[ResourceContext[T_co]],
):
    __slots__ = (
        "_args",
        "_context",
        "_creator",
        "_internal_name",
        "_kwargs",
        "_override",
        "_token",
        "is_async",
    )

    def __init__(
        self,
        creator: typing.Callable[P, typing.Iterator[T_co] | typing.AsyncIterator[T_co]],
        *args: P.args,
        **kwargs: P.kwargs,
    ) -> None:
        super().__init__(creator, *args, **kwargs)
        self._context: ContextVar[ResourceContext[T_co]] = ContextVar(f"{self._creator.__name__}-context")
        self._token: Token[ResourceContext[T_co]] | None = None
        self._lock: Final = asyncio.Lock()

    @override
    def supports_sync_context(self) -> bool:
        return not self.is_async

    def _enter_sync_context(self) -> ResourceContext[T_co]:
        if self.is_async:
            msg = "You must enter async context for async creators."
            raise RuntimeError(msg)
        return self._enter()

    async def _enter_async_context(self) -> ResourceContext[T_co]:
        return self._enter()

    def _enter(self) -> ResourceContext[T_co]:
        self._token = self._context.set(ResourceContext(is_async=self.is_async))
        return self._context.get()

    def _exit_sync_context(self) -> None:
        if not self._token:
            msg = "Context is not set, call ``_enter_sync_context`` first"
            raise RuntimeError(msg)

        try:
            context_item = self._context.get()
            context_item.sync_tear_down()

        finally:
            self._context.reset(self._token)

    async def _exit_async_context(self) -> None:
        if self._token is None:
            msg = "Context is not set, call ``_enter_async_context`` first"
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
    @override
    def sync_context(self) -> typing.Iterator[ResourceContext[T_co]]:
        if self.is_async:
            msg = "Please use async context instead."
            raise RuntimeError(msg)
        token = self._token
        val = self._enter_sync_context()
        temp_token = self._token
        yield val
        self._token = temp_token
        self._exit_sync_context()
        self._token = token

    @contextlib.asynccontextmanager
    @override
    async def async_context(self) -> typing.AsyncIterator[ResourceContext[T_co]]:
        token = self._token

        async with self._lock:
            val = await self._enter_async_context()
            temp_token = self._token
        yield val
        async with self._lock:
            self._token = temp_token
            await self._exit_async_context()
        self._token = token

    @override
    def context(self, func: typing.Callable[P, T]) -> typing.Callable[P, T]:
        """Create a new context manager for the resource, the context manager will be async if the resource is async.

        Returns:
            typing.ContextManager[ResourceContext[T_co]] | typing.AsyncContextManager[ResourceContext[T_co]]:
            A context manager for the resource.

        """
        if inspect.iscoroutinefunction(func):

            @wraps(func)
            async def _async_wrapper(*args: P.args, **kwargs: P.kwargs) -> T:
                async with self.async_context():
                    return await func(*args, **kwargs)  # type: ignore[no-any-return]

            return typing.cast(typing.Callable[P, T], _async_wrapper)

        # wrapped function is sync
        @wraps(func)
        def _sync_wrapper(*args: P.args, **kwargs: P.kwargs) -> T:
            with self.sync_context():
                return func(*args, **kwargs)

        return typing.cast(typing.Callable[P, T], _sync_wrapper)

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
        *context_items: SupportsContext[typing.Any],
        global_context: ContextType | None = None,
        preserve_global_context: bool = False,
        reset_all_containers: bool = False,
    ) -> None:
        """Initialize a new container context.

        Args:
            *context_items: context items to initialize new context for.
            global_context: existing context to use
            preserve_global_context: whether to preserve old global
                context.
            reset_all_containers: Create a new context for all
                containers.
        Will merge old context with the new context if this option is set to True.

        """
        if preserve_global_context and global_context:
            self._initial_context = {**_get_container_context(), **global_context}
        else:
            self._initial_context: ContextType = (  # type: ignore[no-redef]
                _get_container_context() if preserve_global_context else global_context or {}
            )
        self._context_token: Token[ContextType] | None = None
        self._context_items: set[SupportsContext[typing.Any]] = set(context_items)
        self._reset_resource_context: typing.Final[bool] = (
            not context_items and not global_context
        ) or reset_all_containers
        if self._reset_resource_context:
            self._add_providers_from_containers(BaseContainerMeta.get_instances())

        self._context_stack: contextlib.AsyncExitStack | contextlib.ExitStack | None = None

    def _add_providers_from_containers(self, containers: list[ContainerType]) -> None:
        for container in containers:
            for container_provider in container.get_providers().values():
                if isinstance(container_provider, ContextResource):
                    self._context_items.add(container_provider)

    def __enter__(self) -> ContextType:
        self._context_stack = contextlib.ExitStack()
        for item in self._context_items:
            if item.supports_sync_context():
                self._context_stack.enter_context(item.sync_context())
        return self._enter_globals()

    async def __aenter__(self) -> ContextType:
        self._context_stack = contextlib.AsyncExitStack()
        for item in self._context_items:
            await self._context_stack.enter_async_context(item.async_context())
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
                async with container_context(*self._context_items, reset_all_containers=self._reset_resource_context):
                    return await func(*args, **kwargs)  # type: ignore[no-any-return]

            return typing.cast(typing.Callable[P, T_co], _async_inner)

        @wraps(func)
        def _sync_inner(*args: P.args, **kwargs: P.kwargs) -> T_co:
            with container_context(*self._context_items, reset_all_containers=self._reset_resource_context):
                return func(*args, **kwargs)

        return _sync_inner


class DIContextMiddleware:
    def __init__(
        self,
        app: ASGIApp,
        *context_items: SupportsContext[typing.Any],
        global_context: dict[str, typing.Any] | None = None,
        reset_all_containers: bool = True,
    ) -> None:
        self.app: typing.Final = app
        self._context_items: set[SupportsContext[typing.Any]] = set(context_items)
        self._global_context: dict[str, typing.Any] | None = global_context
        self._reset_all_containers: bool = reset_all_containers

    async def __call__(self, scope: Scope, receive: Receive, send: Send) -> None:
        if self._context_items:
            pass
        async with (
            container_context(*self._context_items, global_context=self._global_context)
            if self._context_items
            else container_context(global_context=self._global_context, reset_all_containers=self._reset_all_containers)
        ):
            return await self.app(scope, receive, send)
