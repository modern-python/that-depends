import abc
import typing


T = typing.TypeVar("T")


class AbstractProvider(typing.Generic[T], abc.ABC):
    """Abstract Provider Class."""

    @abc.abstractmethod
    async def async_resolve(self) -> T:
        """Resolve dependency asynchronously."""

    @abc.abstractmethod
    def sync_resolve(self) -> T:
        """Resolve dependency synchronously."""

    async def __call__(self) -> T:
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
