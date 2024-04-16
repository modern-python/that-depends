import abc
import typing


T = typing.TypeVar("T")


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
