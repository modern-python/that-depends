import abc
import contextlib
import inspect
import typing


T = typing.TypeVar("T")
P = typing.ParamSpec("P")


class AbstractProvider(typing.Generic[T], abc.ABC):
    """Abstract Provider Class."""

    @abc.abstractmethod
    async def resolve(self) -> T:
        """Resolve dependency."""

    async def __call__(self) -> T:
        return await self.resolve()

    def override(self, mock: object) -> None:
        self._override = mock

    def reset_override(self) -> None:
        self._override = None


class AbstractResource(AbstractProvider[T], abc.ABC):
    """Abstract Resource Class."""

    @abc.abstractmethod
    async def tear_down(self) -> None:
        """Tear down dependency."""


class Resource(AbstractResource[T]):
    def __init__(
        self,
        creator: typing.Callable[[], typing.Iterator[typing.Any]],
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
        if self._instance:
            self._instance = None

    async def resolve(self) -> T:
        if self._override:
            return typing.cast(T, self._override)

        if not self._instance:
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
        creator: typing.Callable[[], typing.AsyncIterator[typing.Any]],
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
        if self._instance:
            self._instance = None

    async def resolve(self) -> T:
        if self._override:
            return typing.cast(T, self._override)

        if not self._instance:
            self._instance = typing.cast(
                T,
                await self._context_stack.enter_async_context(
                    contextlib.asynccontextmanager(self._creator)(*self._args, **self._kwargs),
                ),
            )
        return self._instance


class Factory(AbstractProvider[T]):
    def __init__(self, factory: type[T] | typing.Callable[P, T], *args: P.args, **kwargs: P.kwargs) -> None:
        self._factory = factory
        self._args = args
        self._kwargs = kwargs
        self._override = None

    async def resolve(self) -> T:
        if self._override:
            return typing.cast(T, self._override)

        return self._factory(
            *[await x() if isinstance(x, AbstractProvider) else x for x in self._args],
            **{k: await v() if isinstance(v, AbstractProvider) else v for k, v in self._kwargs.items()},
        )


class List(AbstractProvider[T]):
    def __init__(self, *providers: AbstractProvider[typing.Any]) -> None:
        self._providers = providers

    async def resolve(self) -> list[T]:  # type: ignore[override]
        return [await x.resolve() for x in self._providers]

    async def __call__(self) -> list[T]:  # type: ignore[override]
        return await self.resolve()


class Singleton(AbstractProvider[T]):
    def __init__(self, factory: type[T] | typing.Callable[P, T], *args: P.args, **kwargs: P.kwargs) -> None:
        self._factory = factory
        self._args = args
        self._kwargs = kwargs
        self._override = None
        self._instance: T | None = None

    async def resolve(self) -> T:
        if self._override:
            return typing.cast(T, self._override)

        if not self._instance:
            self._instance = self._factory(
                *[await x() if isinstance(x, AbstractProvider) else x for x in self._args],
                **{k: await v() if isinstance(v, AbstractProvider) else v for k, v in self._kwargs.items()},
            )
        return self._instance
