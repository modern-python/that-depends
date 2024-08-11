import abc
import contextlib
import typing
from contextlib import contextmanager


T = typing.TypeVar("T")
R = typing.TypeVar("R")
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
    __slots__ = "_context_stack", "_instance"

    def __init__(
        self,
        context_stack: contextlib.AsyncExitStack | contextlib.ExitStack,
        instance: T_co,
    ) -> None:
        self._context_stack = context_stack
        self._instance = instance

    def fetch_instance(self) -> T_co:
        return self._instance

    async def tear_down(self) -> None:
        if isinstance(self._context_stack, contextlib.AsyncExitStack):
            await self._context_stack.aclose()
        else:
            self._context_stack.close()


class AbstractResource(AbstractProvider[T], abc.ABC):
    """Abstract Resource Class."""


class AbstractFactory(AbstractProvider[T], abc.ABC):
    """Abstract Factory Class."""

    @property
    def provider(self) -> typing.Callable[[], typing.Coroutine[typing.Any, typing.Any, T]]:
        return self.async_resolve

    @property
    def sync_provider(self) -> typing.Callable[[], T]:
        return self.sync_resolve
