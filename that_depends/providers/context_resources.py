import asyncio
import contextlib
import inspect
import logging
import typing
import uuid
from contextvars import ContextVar

from that_depends.providers.base import AbstractProvider, AbstractResource
from that_depends.providers.resources import AsyncResource, Resource


T = typing.TypeVar("T")
P = typing.ParamSpec("P")
context: ContextVar[dict[str, AbstractResource[typing.Any]]] = ContextVar("context")
logger = logging.getLogger(__name__)

AppType = typing.TypeVar("AppType")
Scope = typing.MutableMapping[str, typing.Any]
Message = typing.MutableMapping[str, typing.Any]
Receive = typing.Callable[[], typing.Awaitable[Message]]
Send = typing.Callable[[Message], typing.Awaitable[None]]
ASGIApp = typing.Callable[[Scope, Receive, Send], typing.Awaitable[None]]


@contextlib.asynccontextmanager
async def container_context() -> typing.AsyncIterator[None]:
    token = context.set({})
    try:
        yield
    finally:
        results = await asyncio.gather(
            *[provider.tear_down() for _, provider in context.get().items()], return_exceptions=True
        )
        for exception in results:
            if isinstance(exception, Exception):  # pragma: no cover
                logger.error("Error in resource tear down", exc_info=exception)
        context.reset(token)


class DIContextMiddleware:
    def __init__(self, app: ASGIApp) -> None:
        self.app = app

    @container_context()
    async def __call__(self, scope: Scope, receive: Receive, send: Send) -> None:
        return await self.app(scope, receive, send)


def _get_context() -> dict[str, AbstractResource[typing.Any]]:
    try:
        return context.get()
    except LookupError as exc:
        msg = "Context is not set. Use container_context"
        raise RuntimeError(msg) from exc


class ContextResource(AbstractProvider[T]):
    def __init__(
        self,
        creator: typing.Callable[P, typing.Iterator[T]],
        *args: P.args,
        **kwargs: P.kwargs,
    ) -> None:
        if not inspect.isgeneratorfunction(creator):
            msg = "ContextResource must be generator function"
            raise RuntimeError(msg)

        self._creator = creator
        self._args = args
        self._kwargs = kwargs
        self._override = None
        self._internal_name = f"{type(self).__name__}-{uuid.uuid4()}"

    def _get_or_create_resource(self) -> AbstractResource[T]:
        context_obj = _get_context()
        if not (resource := context_obj.get(self._internal_name)):
            resource = Resource(self._creator, *self._args, **self._kwargs)
            context_obj[self._internal_name] = resource

        return resource

    async def async_resolve(self) -> T:
        if self._override:
            return typing.cast(T, self._override)

        return await self._get_or_create_resource().async_resolve()

    def sync_resolve(self) -> T:
        if self._override:
            return typing.cast(T, self._override)

        return self._get_or_create_resource().sync_resolve()


class AsyncContextResource(AbstractProvider[T]):
    def __init__(
        self,
        creator: typing.Callable[P, typing.AsyncIterator[T]],
        *args: P.args,
        **kwargs: P.kwargs,
    ) -> None:
        if not inspect.isasyncgenfunction(creator):
            msg = "AsyncContextResource must be async generator function"
            raise RuntimeError(msg)

        self._creator = creator
        self._args = args
        self._kwargs = kwargs
        self._override = None
        self._internal_name = f"{type(self).__name__}-{uuid.uuid4()}"

    def _get_or_create_resource(self) -> AbstractResource[T]:
        context_obj = _get_context()
        if not (resource := context_obj.get(self._internal_name)):
            resource = AsyncResource(self._creator, *self._args, **self._kwargs)
            context_obj[self._internal_name] = resource

        return resource

    async def async_resolve(self) -> T:
        if self._override:
            return typing.cast(T, self._override)

        return await self._get_or_create_resource().async_resolve()

    def sync_resolve(self) -> T:
        if self._override:
            return typing.cast(T, self._override)

        return self._get_or_create_resource().sync_resolve()
