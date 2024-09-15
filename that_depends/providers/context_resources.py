import inspect
import logging
import typing
import uuid
import warnings
from contextlib import AbstractAsyncContextManager, AbstractContextManager
from contextvars import ContextVar, Token
from functools import wraps
from types import TracebackType

from that_depends.providers.base import AbstractResource, ResourceContext


logger: typing.Final = logging.getLogger(__name__)
T = typing.TypeVar("T")
P = typing.ParamSpec("P")
context_var: ContextVar[dict[str, typing.Any]] = ContextVar("context")
AppType = typing.TypeVar("AppType")
Scope = typing.MutableMapping[str, typing.Any]
Message = typing.MutableMapping[str, typing.Any]
Receive = typing.Callable[[], typing.Awaitable[Message]]
Send = typing.Callable[[Message], typing.Awaitable[None]]
ASGIApp = typing.Callable[[Scope, Receive, Send], typing.Awaitable[None]]

"""
@contextlib.asynccontextmanager
async def container_context(initial_context: dict[str, typing.Any] | None = None) -> typing.AsyncIterator[None]:
    token: typing.Final = context_var.set(initial_context or {})
    try:
        yield
    finally:
        try:
            for context_item in reversed(context_var.get().values()):
                if isinstance(context_item, ResourceContext):
                    await context_item.tear_down()
        finally:
            context_var.reset(token)
"""


ContextType = dict[str, typing.Any]


class container_context(  # noqa: N801
    AbstractAsyncContextManager[ContextType], AbstractContextManager[ContextType]
):
    """Manage the context of ContextResources.

    Can be entered using ``async with container_context()`` or with ``with container_context()``
    as a async-context-manager or context-manager respectively.
    When used as an async-context-manager, it will allow setup & teardown of both sync and async resources.
    When used as an sync-context-manager, it will only allow setup & teardown of sync resources.
    """

    def __init__(self, initial_context: ContextType | None = None) -> None:
        self._initial_context: ContextType | None = initial_context
        self._context_token: Token[ContextType] | None = None

    def __enter__(self) -> ContextType:
        return self._enter()

    async def __aenter__(self) -> ContextType:
        return self._enter()

    def _enter(self) -> ContextType:
        self._context_token = context_var.set(self._initial_context or {})
        return context_var.get()

    def __exit__(
        self, exc_type: type[BaseException] | None, exc_value: BaseException | None, traceback: TracebackType | None
    ) -> None:
        if self._context_token is None:
            msg = "Context is not set, call ``__enter__`` first"
            raise RuntimeError(msg)
        try:
            for context_item in reversed(context_var.get().values()):
                if isinstance(context_item, ResourceContext):
                    # we don't need to handle the case where the ResourceContext is async
                    context_item.sync_tear_down()

        finally:
            context_var.reset(self._context_token)

    async def __aexit__(
        self, exc_type: type[BaseException] | None, exc_val: BaseException | None, traceback: TracebackType | None
    ) -> None:
        if self._context_token is None:
            msg = "Context is not set, call ``__aenter__`` first"
            raise RuntimeError(msg)
        try:
            for context_item in reversed(context_var.get().values()):
                if isinstance(context_item, ResourceContext):
                    if context_item.is_async:
                        await context_item.tear_down()
                    else:
                        context_item.sync_tear_down()
        finally:
            context_var.reset(self._context_token)

    def __call__(self, func: typing.Callable[P, T]) -> typing.Callable[P, T]:
        if inspect.iscoroutinefunction(func):

            @wraps(func)
            async def _async_inner(*args: P.args, **kwds: P.kwargs) -> T:
                async with self:
                    return await func(*args, **kwds)  # type: ignore[no-any-return]

            return typing.cast(typing.Callable[P, T], _async_inner)

        @wraps(func)
        def _sync_inner(*args: P.args, **kwds: P.kwargs) -> T:
            with self:
                return func(*args, **kwds)

        return _sync_inner


class DIContextMiddleware:
    def __init__(self, app: ASGIApp) -> None:
        self.app: typing.Final = app

    @container_context()
    async def __call__(self, scope: Scope, receive: Receive, send: Send) -> None:
        return await self.app(scope, receive, send)


def _get_container_context() -> dict[str, typing.Any]:
    try:
        return context_var.get()
    except LookupError as exc:
        msg = "Context is not set. Use container_context"
        raise RuntimeError(msg) from exc


def fetch_context_item(key: str, default: typing.Any = None) -> typing.Any:  # noqa: ANN401
    return _get_container_context().get(key, default)


class ContextResource(AbstractResource[T]):
    __slots__ = (
        "_is_async",
        "_creator",
        "_args",
        "_kwargs",
        "_override",
        "_internal_name",
    )

    def __init__(
        self,
        creator: typing.Callable[P, typing.Iterator[T] | typing.AsyncIterator[T]],
        *args: P.args,
        **kwargs: P.kwargs,
    ) -> None:
        super().__init__(creator, *args, **kwargs)
        self._internal_name: typing.Final = f"{creator.__name__}-{uuid.uuid4()}"

    def _fetch_context(self) -> ResourceContext[T]:
        container_context_ = _get_container_context()
        if resource_context := container_context_.get(self._internal_name):
            return typing.cast(ResourceContext[T], resource_context)

        resource_context = ResourceContext()
        container_context_[self._internal_name] = resource_context
        return resource_context


class AsyncContextResource(ContextResource[T]):
    def __init__(
        self,
        creator: typing.Callable[P, typing.AsyncIterator[T]],
        *args: P.args,
        **kwargs: P.kwargs,
    ) -> None:
        warnings.warn("AsyncContextResource is deprecated, use ContextResource instead", RuntimeWarning, stacklevel=1)
        super().__init__(creator, *args, **kwargs)
