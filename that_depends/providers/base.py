import abc
import asyncio
import contextlib
import inspect
import typing
from contextlib import contextmanager


T = typing.TypeVar("T")
R = typing.TypeVar("R")
P = typing.ParamSpec("P")
T_co = typing.TypeVar("T_co", covariant=True)


class AbstractProvider(typing.Generic[T_co], abc.ABC):
    """Abstract Provider Class."""

    @abc.abstractmethod
    async def async_resolve(self) -> T_co:
        """Resolve dependency asynchronously."""

    @abc.abstractmethod
    def sync_resolve(self) -> T_co:
        """Resolve dependency synchronously."""

    async def __call__(self) -> T_co:
        return await self.async_resolve()

    def override(self, mock: object) -> None:
        self._override = mock

    @contextmanager
    def override_context(self, mock: object) -> typing.Iterator[None]:
        self.override(mock)
        try:
            yield
        finally:
            self.reset_override()

    def reset_override(self) -> None:
        self._override = None

    @property
    def cast(self) -> T_co:
        """Returns self, but cast to the type of the provided value.

        This helps to pass providers as input to other providers while avoiding type checking errors:

            class A: ...

            def create_b(a: A) -> B: ...

            class Container(BaseContainer):
                a_factory = Factory(A)
                b_factory1 = Factory(create_b, a_factory)  # works, but mypy (or pyright, etc.) will complain
                b_factory2 = Factory(create_b, a_factory.cast)  # works and passes type checking
        """
        return typing.cast(T_co, self)


class ResourceContext(typing.Generic[T_co]):
    __slots__ = "context_stack", "instance", "resolving_lock"

    def __init__(
        self,
        context_stack: contextlib.AsyncExitStack | contextlib.ExitStack | None = None,
        instance: T_co | None = None,
    ) -> None:
        self.instance = instance
        self.resolving_lock = asyncio.Lock()
        self.context_stack = context_stack

    async def tear_down(self) -> None:
        if self.context_stack is None:
            return

        if isinstance(self.context_stack, contextlib.AsyncExitStack):
            await self.context_stack.aclose()
        else:
            self.context_stack.close()
        self.context_stack = None
        self.instance = None


class AbstractResource(AbstractProvider[T], abc.ABC):
    def __init__(
        self,
        creator: typing.Callable[P, typing.Iterator[T] | typing.AsyncIterator[T]],
        *args: P.args,
        **kwargs: P.kwargs,
    ) -> None:
        if inspect.isasyncgenfunction(creator):
            self._is_async = True
        elif inspect.isgeneratorfunction(creator):
            self._is_async = False
        else:
            msg = f"{type(self).__name__} must be generator function"
            raise RuntimeError(msg)

        self._creator = creator
        self._args = args
        self._kwargs = kwargs
        self._override = None

    def _is_creator_async(
        self, _: typing.Callable[P, typing.Iterator[T] | typing.AsyncIterator[T]]
    ) -> typing.TypeGuard[typing.Callable[P, typing.AsyncIterator[T]]]:
        return self._is_async

    def _is_creator_sync(
        self, _: typing.Callable[P, typing.Iterator[T] | typing.AsyncIterator[T]]
    ) -> typing.TypeGuard[typing.Callable[P, typing.Iterator[T]]]:
        return not self._is_async

    @abc.abstractmethod
    def _fetch_context(self) -> ResourceContext[T]: ...

    async def async_resolve(self) -> T:
        if self._override:
            return typing.cast(T, self._override)

        context = self._fetch_context()
        if context.instance is not None:
            return context.instance

        # lock to prevent race condition while resolving
        async with context.resolving_lock:
            if context.instance is None:
                if self._is_creator_async(self._creator):
                    context.context_stack = contextlib.AsyncExitStack()
                    context.instance = typing.cast(
                        T,
                        await context.context_stack.enter_async_context(
                            contextlib.asynccontextmanager(self._creator)(
                                *[await x() if isinstance(x, AbstractProvider) else x for x in self._args],
                                **{
                                    k: await v() if isinstance(v, AbstractProvider) else v
                                    for k, v in self._kwargs.items()
                                },
                            ),
                        ),
                    )
                elif self._is_creator_sync(self._creator):
                    context.context_stack = contextlib.ExitStack()
                    context.instance = context.context_stack.enter_context(
                        contextlib.contextmanager(self._creator)(
                            *[await x.async_resolve() if isinstance(x, AbstractProvider) else x for x in self._args],
                            **{
                                k: await v.async_resolve() if isinstance(v, AbstractProvider) else v
                                for k, v in self._kwargs.items()
                            },
                        ),
                    )
            return typing.cast(T, context.instance)

    def sync_resolve(self) -> T:
        if self._override:
            return typing.cast(T, self._override)

        context = self._fetch_context()
        if context.instance is not None:
            return context.instance

        if self._is_creator_async(self._creator):
            msg = "AsyncResource cannot be resolved synchronously"
            raise RuntimeError(msg)

        if self._is_creator_sync(self._creator):
            context.context_stack = contextlib.ExitStack()
            context.instance = context.context_stack.enter_context(
                contextlib.contextmanager(self._creator)(
                    *[x.sync_resolve() if isinstance(x, AbstractProvider) else x for x in self._args],
                    **{k: v.sync_resolve() if isinstance(v, AbstractProvider) else v for k, v in self._kwargs.items()},
                ),
            )
        return typing.cast(T, context.instance)


class AbstractFactory(AbstractProvider[T], abc.ABC):
    """Abstract Factory Class."""

    @property
    def provider(self) -> typing.Callable[[], typing.Coroutine[typing.Any, typing.Any, T]]:
        return self.async_resolve

    @property
    def sync_provider(self) -> typing.Callable[[], T]:
        return self.sync_resolve
