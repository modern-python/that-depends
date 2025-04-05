import asyncio
import random
import typing

import pytest
from typing_extensions import override

from that_depends import BaseContainer
from that_depends.providers.base import AbstractProvider
from that_depends.providers.local_singleton import ThreadLocalSingleton
from that_depends.providers.mixin import SupportsTeardown
from that_depends.providers.resources import Resource
from that_depends.providers.singleton import AsyncSingleton, Singleton


class DummyProvider(SupportsTeardown, AbstractProvider[int]):
    """A dummy provider used for testing."""

    def __init__(self) -> None:
        super().__init__()
        self._instance: int | None = None

    @override
    async def tear_down(self, propagate: bool = True) -> None:
        self._instance = None
        if propagate:
            await self._tear_down_children()

    @override
    def tear_down_sync(self, propagate: bool = True, raise_on_async: bool = True) -> None:
        self._instance = None
        if propagate:
            self._tear_down_children_sync(propagate=propagate, raise_on_async=raise_on_async)

    @override
    async def resolve(self) -> int:
        self._instance = 1
        return self._instance

    @override
    def resolve_sync(self) -> int:
        self._instance = 1
        return self._instance  # pragma: no cover


def test_add_child_provider() -> None:
    provider_a = DummyProvider()
    provider_b = DummyProvider()

    assert len(provider_a._children) == 0, "Expected provider_a to have no children initially"
    provider_a.add_child_provider(provider_b)

    assert len(provider_a._children) == 1, "Expected provider_a._children to have 1 child"
    assert provider_b in provider_a._children, "provider_b should be in provider_a._children"


def test_register_with_providers() -> None:
    parent = DummyProvider()
    child_1 = DummyProvider()
    child_2 = DummyProvider()

    parent._register([child_1, child_2])

    assert parent in child_1._children, "Expected child_1._children to contain parent"
    assert parent in child_2._children, "Expected child_2._children to contain parent"


def test_register_with_mixed_items() -> None:
    parent = DummyProvider()
    child_1 = DummyProvider()
    non_provider = 12345  # not an AbstractProvider

    parent._register([child_1, non_provider])

    assert parent in child_1._children, "Expected child_1._children to contain parent"


def test_sync_tear_down_propagation() -> None:
    parent = DummyProvider()
    child_1 = DummyProvider()
    child_2 = DummyProvider()

    parent.add_child_provider(child_1)
    parent.add_child_provider(child_2)

    assert parent.resolve_sync() == 1

    assert parent._instance == 1

    parent.tear_down_sync()

    assert parent._instance is None
    assert child_1._instance is None
    assert child_2._instance is None


async def test_async_tear_down_propagation() -> None:
    parent = DummyProvider()
    child_1 = DummyProvider()
    child_2 = DummyProvider()

    parent.add_child_provider(child_1)
    parent.add_child_provider(child_2)

    assert await parent.resolve() == 1

    assert parent._instance == 1

    await parent.tear_down()

    assert parent._instance is None
    assert child_1._instance is None
    assert child_2._instance is None


_RETURN_VALUE = 42


def _simple_factory_value() -> int:
    return _RETURN_VALUE


async def _simple_async_factory_value(v: int) -> int:
    await asyncio.sleep(0.001)
    return v


def _resource_generator(v: int) -> typing.Iterator[int]:
    """Sync generator resource with teardown logic."""
    try:
        yield v
    finally:
        # Normally you'd close files, DB connections, etc. here
        pass


@pytest.fixture
def dummy_singleton() -> Singleton[int]:
    """Get sync factory for test use."""
    return Singleton(_simple_factory_value)


def test_singleton_registration_and_deregistration(dummy_singleton: Singleton[int]) -> None:
    singleton = Singleton(lambda x: x + 1, dummy_singleton.cast)
    assert singleton not in dummy_singleton._children, "Singleton should not be registered as child yet."
    singleton.resolve_sync()

    assert singleton in dummy_singleton._children, "Singleton should be registered as a child."

    dummy_singleton.tear_down_sync()

    assert singleton not in dummy_singleton._children, (
        "Singleton should be removed from parent's children after tear_down."
    )


def test_thread_local_singleton_registration_and_deregistration(dummy_singleton: Singleton[int]) -> None:
    thread_local = ThreadLocalSingleton(lambda val: f"TL-{val}", dummy_singleton)

    assert thread_local not in dummy_singleton._children, "ThreadLocalSingleton not registered as child."

    thread_local.resolve_sync()
    assert thread_local in dummy_singleton._children, "ThreadLocalSingleton not registered as child."

    # Teardown
    thread_local.tear_down_sync()

    assert thread_local not in dummy_singleton._children, "ThreadLocalSingleton should be deregistered after teardown."


def test_resource_registration_and_deregistration(dummy_singleton: Singleton[int]) -> None:
    resource = Resource(_resource_generator, dummy_singleton.cast)

    assert resource not in dummy_singleton._children, "Resource should not be registered as child yet."

    resource.resolve_sync()

    assert resource in dummy_singleton._children, "Resource should be registered as child."

    resource.tear_down_sync()
    assert resource not in dummy_singleton._children, "Resource should be deregistered after teardown."


async def test_async_singleton_registration_and_deregistration(dummy_singleton: Singleton[int]) -> None:
    async_singleton = AsyncSingleton(_simple_async_factory_value, dummy_singleton.cast)

    await async_singleton.resolve()

    assert async_singleton in dummy_singleton._children

    value = await async_singleton.resolve()
    assert value == _RETURN_VALUE

    await async_singleton.tear_down()

    assert async_singleton not in dummy_singleton._children


def test_teardown_propagation_chain() -> None:
    def _sync_resource_gen(v: float) -> typing.Iterator[float]:
        try:
            yield v
        finally:
            pass

    def _grandchild_gen() -> typing.Iterator[float]:
        try:
            yield random.random()
        finally:
            pass

    parent_resource = Resource(_grandchild_gen)
    child_singleton = Singleton(lambda g: g + 1.0, parent_resource.cast)
    grandchild = Resource(_sync_resource_gen, child_singleton.cast)

    parent_value = parent_resource.resolve_sync()
    grandchild_value = grandchild.resolve_sync()

    assert child_singleton in parent_resource._children
    assert grandchild in child_singleton._children
    parent_resource.tear_down_sync(propagate=True)

    assert grandchild.resolve_sync() != grandchild_value
    assert parent_resource.resolve_sync() != parent_value


def test_propagate_off() -> None:
    parent = Singleton(_simple_factory_value)
    child = Singleton(lambda x: x + 1, parent.cast)

    child.resolve_sync()

    parent.tear_down_sync(propagate=False)

    assert child in parent._children
    assert child._instance is not None


async def test_async_tear_down_propagation_with_singleton() -> None:
    parent = Singleton(_simple_factory_value)
    child = Singleton(lambda x: x + 1, parent.cast)

    await child.resolve()

    await parent.tear_down()

    assert child._instance is None


async def test_async_propagate_off() -> None:
    parent = Singleton(_simple_factory_value)
    child = Singleton(lambda x: x + 1, parent.cast)

    await child.resolve()

    await parent.tear_down(propagate=False)

    assert child._instance is not None


async def test_provider_registration_in_different_scope_async() -> None:
    async def _creator() -> int:
        return 1

    async def _identity(x: int) -> int:
        return x

    class Container(BaseContainer):
        provider = AsyncSingleton(_creator)

    async def nested() -> int:
        p = AsyncSingleton(_identity, Container.provider.cast)

        result = await p.resolve()

        await p.tear_down()
        assert len(p._parents) == 0
        return result

    await nested()

    assert len(Container.provider._children) == 0


def test_provider_registration_in_different_scope_sync() -> None:
    class Container(BaseContainer):
        provider = Singleton(lambda: 1)

    def nested() -> int:
        p = Singleton(lambda x: x, Container.provider.cast)

        result = p.resolve_sync()

        p.tear_down_sync()
        assert len(p._parents) == 0
        return result

    nested()

    assert len(Container.provider._children) == 0
