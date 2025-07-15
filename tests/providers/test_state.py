import pytest

from that_depends import BaseContainer
from that_depends.exceptions import StateNotInitializedError
from that_depends.providers.state import State


async def test_state_raises_if_not_set_async() -> None:
    class _Container(BaseContainer):
        state: State[str] = State()

    with pytest.raises(StateNotInitializedError):
        await _Container.state.resolve()


def test_state_raises_if_not_set_sync() -> None:
    class _Container(BaseContainer):
        state: State[str] = State()

    with pytest.raises(StateNotInitializedError):
        _Container.state.resolve_sync()


async def test_state_set_resolves_correctly_async() -> None:
    class _Container(BaseContainer):
        state: State[str] = State()

    state_value = "test_value"

    with _Container.state.init(state_value) as value:
        assert value == state_value
        assert await _Container.state.resolve() == state_value


def test_state_set_resolves_correctly_sync() -> None:
    class _Container(BaseContainer):
        state: State[str] = State()

    state_value = "test_value"

    with _Container.state.init(state_value) as value:
        assert value == state_value
        assert _Container.state.resolve_sync() == state_value
