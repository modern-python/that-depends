from typing import TypeVar

from typing_extensions import override

from that_depends.providers import AbstractProvider
from that_depends.utils import UNSET, Unset


T_co = TypeVar("T_co", covariant=True)

_UNSET = object()


class State(AbstractProvider[T_co]):
    """Provides a state that can be resolved with an optional callback."""

    def __init__(self) -> None:
        """Initialize the State provider with an optional callback."""
        super().__init__()
        self._state: T_co | Unset = UNSET

    @override
    async def resolve(self) -> T_co: ...

    @override
    def resolve_sync(self) -> T_co: ...
