import typing
import uuid
from contextlib import contextmanager
from contextvars import ContextVar
from typing import TypeVar

from typing_extensions import override

from that_depends.exceptions import StateNotInitializedError
from that_depends.providers import AbstractProvider
from that_depends.utils import UNSET, Unset, is_set


T = TypeVar("T", covariant=False)

_STATE_UNSET_ERROR_MESSAGE: typing.Final[str] = (
    "State has not been initialized.\n"
    "Please use `with provider.init(state):` to initialize the state before resolving it."
)


class State(AbstractProvider[T]):
    """Provides a value that can be passed into the provider at runtime."""

    def __init__(self) -> None:
        """Create a state provider."""
        super().__init__()

        self._state: ContextVar[T | Unset] = ContextVar(f"STATE_{uuid.uuid4()}", default=UNSET)

    @contextmanager
    def init(self, state: T) -> typing.Iterator[T]:
        """Set the state provider's value.

        Args:
            state: value to store.

        Returns:
            Iterator[T_co]: A context manager that yields the state value.

        """
        token = self._state.set(state)
        yield state
        self._state.reset(token)

    @override
    async def resolve(self) -> T:
        return self.resolve_sync()

    @override
    def resolve_sync(self) -> T:
        value = self._state.get()
        if is_set(value):
            return value
        raise StateNotInitializedError(_STATE_UNSET_ERROR_MESSAGE)
