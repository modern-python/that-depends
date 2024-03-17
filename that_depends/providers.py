import abc
import contextlib
import inspect
import typing


T = typing.TypeVar("T")


class AbstractProvider(typing.Generic[T], abc.ABC):
    """Abstract Provider Class."""

    _is_async: bool

    @abc.abstractmethod
    async def resolve(self) -> T:
        """Resolve dependency."""

    async def __call__(self) -> T:
        return await self.resolve()

    @property
    def lazy(self) -> T:
        return typing.cast(T, self)


class Resource(AbstractProvider[T]):
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

    async def resolve(self) -> T:
        if not self._instance:
            self._instance = typing.cast(
                T,
                self._context_stack.enter_context(
                    contextlib.contextmanager(self._creator)(*self._args, **self._kwargs),
                ),
            )
        return self._instance


class AsyncResource(typing.Generic[T], AbstractProvider[T]):
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

    async def resolve(self) -> T:
        if not self._instance:
            self._instance = typing.cast(
                T,
                await self._context_stack.enter_async_context(
                    contextlib.asynccontextmanager(self._creator)(*self._args, **self._kwargs),
                ),
            )
        return self._instance


class Factory(typing.Generic[T], AbstractProvider[T]):
    def __init__(self, factory: type[T], *args: typing.Any, **kwargs: typing.Any) -> None:  # noqa: ANN401
        self._factory = factory
        self._args = args
        self._kwargs = kwargs

    async def resolve(self) -> T:
        return self._factory(
            *[await x() if isinstance(x, AbstractProvider) else x for x in self._args],
            **{k: await v() if isinstance(v, AbstractProvider) else v for k, v in self._kwargs.items()},
        )
