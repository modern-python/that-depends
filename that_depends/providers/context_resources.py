import contextlib
import logging
import typing
import uuid
import warnings
from contextvars import ContextVar

from that_depends.providers.base import AbstractResource, ResourceContext


T = typing.TypeVar("T")
P = typing.ParamSpec("P")
context_var: ContextVar[dict[str, typing.Any]] = ContextVar("context")
logger = logging.getLogger(__name__)

AppType = typing.TypeVar("AppType")
Scope = typing.MutableMapping[str, typing.Any]
Message = typing.MutableMapping[str, typing.Any]
Receive = typing.Callable[[], typing.Awaitable[Message]]
Send = typing.Callable[[Message], typing.Awaitable[None]]
ASGIApp = typing.Callable[[Scope, Receive, Send], typing.Awaitable[None]]


@contextlib.asynccontextmanager
async def container_context(initial_context: dict[str, typing.Any] | None = None) -> typing.AsyncIterator[None]:
    token = context_var.set(initial_context or {})
    try:
        yield
    finally:
        try:
            for context_item in reversed(context_var.get().values()):
                if isinstance(context_item, ResourceContext):
                    await context_item.tear_down()
        finally:
            context_var.reset(token)


class DIContextMiddleware:
    def __init__(self, app: ASGIApp) -> None:
        self.app = app

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
        self._internal_name = f"{creator.__name__}-{uuid.uuid4()}"

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
