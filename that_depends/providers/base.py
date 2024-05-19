import abc
import typing


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

    def reset_override(self) -> None:
        self._override = None


class AbstractResource(AbstractProvider[T], abc.ABC):
    """Abstract Resource Class."""

    @abc.abstractmethod
    async def tear_down(self) -> None:
        """Tear down dependency."""
