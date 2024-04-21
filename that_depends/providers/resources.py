import contextlib
import inspect
import typing

from that_depends.providers.base import AbstractResource


T = typing.TypeVar("T")
P = typing.ParamSpec("P")


class Resource(AbstractResource[T]):
    def __init__(
        self,
        creator: typing.Callable[..., typing.Iterator[T]],
        *args: typing.Any,  # noqa: ANN401
        **kwargs: typing.Any,  # noqa: ANN401
    ) -> None:
        if not inspect.isgeneratorfunction(creator):
            msg = "Resource must be generator function"
            raise RuntimeError(msg)

        self._creator = creator
        self._context_stack = contextlib.ExitStack()
        self._args = args
        self._kwargs = kwargs
        self._instance: T | None = None
        self._override = None

    async def tear_down(self) -> None:
        if self._context_stack:
            self._context_stack.close()
        if self._instance is not None:
            self._instance = None

    async def resolve(self) -> T:
        if self._override:
            return typing.cast(T, self._override)

        if self._instance is None:
            self._instance = typing.cast(
                T,
                self._context_stack.enter_context(
                    contextlib.contextmanager(self._creator)(*self._args, **self._kwargs),
                ),
            )
        return self._instance


class AsyncResource(AbstractResource[T]):
    def __init__(
        self,
        creator: typing.Callable[..., typing.AsyncIterator[T]],
        *args: typing.Any,  # noqa: ANN401
        **kwargs: typing.Any,  # noqa: ANN401
    ) -> None:
        if not inspect.isasyncgenfunction(creator):
            msg = "AsyncResource must be async generator function"
            raise RuntimeError(msg)

        self._creator = creator
        self._context_stack = contextlib.AsyncExitStack()
        self._args = args
        self._kwargs = kwargs
        self._instance: T | None = None
        self._override = None

    async def tear_down(self) -> None:
        if self._context_stack:
            await self._context_stack.aclose()
        if self._instance is not None:
            self._instance = None

    async def resolve(self) -> T:
        if self._override:
            return typing.cast(T, self._override)

        if self._instance is None:
            self._instance = typing.cast(
                T,
                await self._context_stack.enter_async_context(
                    contextlib.asynccontextmanager(self._creator)(*self._args, **self._kwargs),
                ),
            )
        return self._instance
