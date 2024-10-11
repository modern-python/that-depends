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


class container_context(  # noqa: N801
    AbstractAsyncContextManager[ContextType], AbstractContextManager[ContextType]
):
    """Manage the context of ContextResources.

    Can be entered using ``async with container_context()`` or with ``with container_context()``
    as async-context-manager or context-manager respectively.
    When used as async-context-manager, it will allow setup & teardown of both sync and async resources.
    When used as sync-context-manager, it will only allow setup & teardown of sync resources.
    """

    __slots__ = "_initial_context", "_context_token"

    def __init__(self, initial_context: ContextType | None = None) -> None:
        self._initial_context: ContextType = initial_context or {}
        self._context_token: Token[ContextType] | None = None

    def __enter__(self) -> ContextType:
        self._initial_context[_ASYNC_CONTEXT_KEY] = False
        return self._enter()

    async def __aenter__(self) -> ContextType:
        self._initial_context[_ASYNC_CONTEXT_KEY] = True
        return self._enter()

    def _enter(self) -> ContextType:
        self._context_token = _CONTAINER_CONTEXT.set({**self._initial_context})
        return _CONTAINER_CONTEXT.get()

    def __exit__(
        self, exc_type: type[BaseException] | None, exc_value: BaseException | None, traceback: TracebackType | None
    ) -> None:
        if self._context_token is None:
            msg = "Context is not set, call ``__enter__`` first"
            raise RuntimeError(msg)

        try:
            for context_item in reversed(_CONTAINER_CONTEXT.get().values()):
                if isinstance(context_item, ResourceContext):
                    # we don't need to handle the case where the ResourceContext is async
                    context_item.sync_tear_down()

        finally:
            _CONTAINER_CONTEXT.reset(self._context_token)

    async def __aexit__(
        self, exc_type: type[BaseException] | None, exc_val: BaseException | None, traceback: TracebackType | None
    ) -> None:
        if self._context_token is None:
            msg = "Context is not set, call ``__aenter__`` first"
            raise RuntimeError(msg)

        try:
            for context_item in reversed(_CONTAINER_CONTEXT.get().values()):
                if not isinstance(context_item, ResourceContext):
                    continue

                if context_item.is_context_stack_async(context_item.context_stack):
                    await context_item.tear_down()
                else:
                    context_item.sync_tear_down()
        finally:
            _CONTAINER_CONTEXT.reset(self._context_token)

    def __call__(self, func: typing.Callable[P, T_co]) -> typing.Callable[P, T_co]:
        if inspect.iscoroutinefunction(func):

            @wraps(func)
            async def _async_inner(*args: P.args, **kwargs: P.kwargs) -> T_co:
                async with container_context(self._initial_context):
                    return await func(*args, **kwargs)  # type: ignore[no-any-return]

            return typing.cast(typing.Callable[P, T_co], _async_inner)

        @wraps(func)
        def _sync_inner(*args: P.args, **kwargs: P.kwargs) -> T_co:
            with container_context(self._initial_context):
                return func(*args, **kwargs)

        return _sync_inner


class DIContextMiddleware:
    def __init__(self, app: ASGIApp) -> None:
        self.app: typing.Final = app

    @container_context()
    async def __call__(self, scope: Scope, receive: Receive, send: Send) -> None:
        return await self.app(scope, receive, send)


def _get_container_context() -> dict[str, typing.Any]:
    try:
        return _CONTAINER_CONTEXT.get()
    except LookupError as exc:
        msg = "Context is not set. Use container_context"
        raise RuntimeError(msg) from exc


def _is_container_context_async() -> bool:
    """Check if the current container context is async.

    :return: Whether the current container context is async.
    :rtype: bool
    """
    return typing.cast(bool, _get_container_context().get(_ASYNC_CONTEXT_KEY, False))


def fetch_context_item(key: str, default: typing.Any = None) -> typing.Any:  # noqa: ANN401
    return _get_container_context().get(key, default)


class ContextResource(AbstractResource[T_co]):
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
        creator: typing.Callable[P, typing.Iterator[T_co] | typing.AsyncIterator[T_co]],
        *args: P.args,
        **kwargs: P.kwargs,
    ) -> None:
        super().__init__(creator, *args, **kwargs)
        self._internal_name: typing.Final = f"{creator.__name__}-{uuid.uuid4()}"

    def _fetch_context(self) -> ResourceContext[T_co]:
        container_context = _get_container_context()
        if resource_context := container_context.get(self._internal_name):
            return typing.cast(ResourceContext[T_co], resource_context)

        resource_context = ResourceContext(is_async=_is_container_context_async())
        container_context[self._internal_name] = resource_context
        return resource_context


class AsyncContextResource(ContextResource[T_co]):
    def __init__(
        self,
        creator: typing.Callable[P, typing.AsyncIterator[T_co]],
        *args: P.args,
        **kwargs: P.kwargs,
    ) -> None:
        warnings.warn("AsyncContextResource is deprecated, use ContextResource instead", RuntimeWarning, stacklevel=1)
        super().__init__(creator, *args, **kwargs)
