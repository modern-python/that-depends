import asyncio
import contextlib
import inspect
import typing
import uuid
from contextvars import ContextVar

from that_depends.providers.base import AbstractProvider, AbstractResource
from that_depends.providers.resources import AsyncResource, Resource


T = typing.TypeVar("T")
P = typing.ParamSpec("P")
context: ContextVar[dict[str, AbstractResource[typing.Any]]] = ContextVar("context")


@contextlib.asynccontextmanager
async def container_context() -> typing.AsyncIterator[None]:
    token = context.set({})
    try:
        yield
    finally:
        await asyncio.gather(*[provider.tear_down() for _, provider in context.get().items()], return_exceptions=True)
        context.reset(token)


class ContextResource(AbstractProvider[T]):
    def __init__(
        self,
        creator: typing.Callable[..., typing.Iterator[T]],
        *args: typing.Any,  # noqa: ANN401
        **kwargs: typing.Any,  # noqa: ANN401
    ) -> None:
        if not inspect.isgeneratorfunction(creator):
            msg = "ContextResource must be generator function"
            raise RuntimeError(msg)

        self._creator = creator
        self._args = args
        self._kwargs = kwargs
        self._override = None
        self._internal_name = f"{type(self).__name__}-{uuid.uuid4()}"

    async def resolve(self) -> T:
        if self._override:
            return typing.cast(T, self._override)

        try:
            context_obj = context.get()
        except LookupError as exc:
            msg = "Context is not set. Use container_context"
            raise RuntimeError(msg) from exc

        if not (_resource := context_obj.get(self._internal_name)):
            _resource = Resource(self._creator, *self._args, **self._kwargs)
            context_obj[self._internal_name] = _resource

        return typing.cast(T, await _resource.resolve())


class AsyncContextResource(AbstractProvider[T]):
    def __init__(
        self,
        creator: typing.Callable[..., typing.AsyncIterator[T]],
        *args: typing.Any,  # noqa: ANN401
        **kwargs: typing.Any,  # noqa: ANN401
    ) -> None:
        if not inspect.isasyncgenfunction(creator):
            msg = "AsyncContextResource must be async generator function"
            raise RuntimeError(msg)

        self._creator = creator
        self._args = args
        self._kwargs = kwargs
        self._override = None
        self._internal_name = f"{type(self).__name__}-{uuid.uuid4()}"

    async def resolve(self) -> T:
        if self._override:
            return typing.cast(T, self._override)

        try:
            context_obj = context.get()
        except LookupError as exc:
            msg = "Context is not set. Use container_context"
            raise RuntimeError(msg) from exc

        if not (_resource := context_obj.get(self._internal_name)):
            _resource = AsyncResource(self._creator, *self._args, **self._kwargs)
            context_obj[self._internal_name] = _resource

        return typing.cast(T, await _resource.resolve())
