import asyncio
import random

import pytest

from that_depends import BaseContainer
from that_depends.exceptions import StateNotInitializedError
from that_depends.providers import AsyncFactory, Factory, State


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


async def test_state_correctly_manages_its_context() -> None:
    async def _async_creator(x: int) -> int:
        await asyncio.sleep(random.random())
        return x

    class _Container(BaseContainer):
        state: State[int] = State()
        dependent = Factory(lambda x: x, state.cast)
        async_dependent = AsyncFactory(_async_creator, state.cast)

    async def _main(x: int) -> None:
        with _Container.state.init(x):
            dependent_value = await _Container.dependent.resolve()
            assert dependent_value == x
            async_dependent_value = await _Container.async_dependent.resolve()
            assert async_dependent_value == x
            new_x = x + random.randint(1, 1000)
            with _Container.state.init(new_x):
                dependent_value = await _Container.dependent.resolve()
                assert dependent_value == new_x
                async_dependent_value = await _Container.async_dependent.resolve()
                assert async_dependent_value == new_x

            dependent_value = await _Container.dependent.resolve()
            assert dependent_value == x
            async_dependent_value = await _Container.async_dependent.resolve()
            assert async_dependent_value == x

    tasks = [_main(x) for x in range(10)]

    await asyncio.gather(*tasks)
