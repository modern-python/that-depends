import contextlib
import inspect
import typing

from that_depends.providers.base import AbstractProvider, AbstractResource


T = typing.TypeVar("T")
P = typing.ParamSpec("P")


class Resource(AbstractResource[T]):
    def __init__(
        self,
        creator: typing.Callable[P, typing.Iterator[T]],
        *args: P.args,
        **kwargs: P.kwargs,
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

    async def async_resolve(self) -> T:
        if self._override:
            return typing.cast(T, self._override)

        if self._instance is None:
            self._instance = typing.cast(
                T,
                self._context_stack.enter_context(
                    contextlib.contextmanager(self._creator)(
                        *[await x.async_resolve() if isinstance(x, AbstractProvider) else x for x in self._args],
                        **{
                            k: await v.async_resolve() if isinstance(v, AbstractProvider) else v
                            for k, v in self._kwargs.items()
                        },
                    ),
                ),
            )
        return self._instance

    def sync_resolve(self) -> T:
        if self._override:
            return typing.cast(T, self._override)

        if self._instance is None:
            self._instance = typing.cast(
                T,
                self._context_stack.enter_context(
                    contextlib.contextmanager(self._creator)(
                        *[x.sync_resolve() if isinstance(x, AbstractProvider) else x for x in self._args],
                        **{
                            k: v.sync_resolve() if isinstance(v, AbstractProvider) else v
                            for k, v in self._kwargs.items()
                        },
                    ),
                ),
            )
        return self._instance


class AsyncResource(AbstractResource[T]):
    def __init__(
        self,
        creator: typing.Callable[P, typing.AsyncIterator[T]],
        *args: P.args,
        **kwargs: P.kwargs,
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

    async def async_resolve(self) -> T:
        if self._override:
            return typing.cast(T, self._override)

        if self._instance is None:
            self._instance = typing.cast(
                T,
                await self._context_stack.enter_async_context(
                    contextlib.asynccontextmanager(self._creator)(
                        *[await x() if isinstance(x, AbstractProvider) else x for x in self._args],
                        **{k: await v() if isinstance(v, AbstractProvider) else v for k, v in self._kwargs.items()},
                    ),
                ),
            )
        return self._instance

    def sync_resolve(self) -> T:
        if self._override:
            return typing.cast(T, self._override)

        if self._instance is None:
            msg = "AsyncResource cannot be resolved synchronously"
            raise RuntimeError(msg)

        return self._instance
