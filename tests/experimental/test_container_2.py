import random
from collections.abc import AsyncIterator, Iterator

import pytest
import typing_extensions

from that_depends import BaseContainer, ContextScopes, container_context, providers
from that_depends.experimental import LazyProvider


class _RandomWrapper:
    def __init__(self) -> None:
        self.value = random.random()

    @typing_extensions.override
    def __eq__(self, other: object) -> bool:
        if isinstance(other, _RandomWrapper):
            return self.value == other.value
        return False  # pragma: nocover

    def __hash__(self) -> int:
        return 0  # pragma: nocover


async def _async_creator() -> AsyncIterator[float]:
    yield random.random()


def _sync_creator() -> Iterator[_RandomWrapper]:
    yield _RandomWrapper()


class Container2(BaseContainer):
    """Test Container 2."""

    alias = "container_2"
    default_scope = ContextScopes.APP
    obj_1 = LazyProvider("tests.experimental.test_container_1.Container1.obj_1")
    obj_2 = providers.Object(2)
    async_context_provider = providers.ContextResource(_async_creator)
    sync_context_provider = providers.ContextResource(_sync_creator)
    singleton_provider = providers.Singleton(random.random)


async def test_lazy_provider_resolution_async() -> None:
    assert await Container2.obj_1.resolve() == 1


def test_lazy_provider_override_sync() -> None:
    override_value = 42
    Container2.obj_1.override_sync(override_value)
    assert Container2.obj_1.resolve_sync() == override_value
    Container2.obj_1.reset_override_sync()
    assert Container2.obj_1.resolve_sync() == 1


async def test_lazy_provider_override_async() -> None:
    override_value = 42
    await Container2.obj_1.override(override_value)
    assert await Container2.obj_1.resolve() == override_value
    await Container2.obj_1.reset_override()
    assert await Container2.obj_1.resolve() == 1


def test_lazy_provider_invalid_state() -> None:
    lazy_provider = LazyProvider(
        module_string="tests.experimental.test_container_2", provider_string="Container2.sync_context_provider"
    )
    lazy_provider._module_string = None
    with pytest.raises(RuntimeError):
        lazy_provider.resolve_sync()


async def test_lazy_provider_context_resource_async() -> None:
    lazy_provider = LazyProvider("tests.experimental.test_container_2.Container2.async_context_provider")
    async with lazy_provider.context_async(force=True):
        assert await lazy_provider.resolve() == await Container2.async_context_provider.resolve()
        async with Container2.async_context_provider.context_async(force=True):
            assert await lazy_provider.resolve() == await Container2.async_context_provider.resolve()

    with pytest.raises(RuntimeError):
        await lazy_provider.resolve()

    async with container_context(Container2, scope=ContextScopes.APP):
        assert await lazy_provider.resolve() == await Container2.async_context_provider.resolve()

    assert lazy_provider.get_scope() == ContextScopes.APP

    assert lazy_provider.supports_context_sync() is False


def test_lazy_provider_context_resource_sync() -> None:
    lazy_provider = LazyProvider("tests.experimental.test_container_2.Container2.sync_context_provider")
    with lazy_provider.context_sync(force=True):
        assert lazy_provider.resolve_sync() == Container2.sync_context_provider.resolve_sync()
        with Container2.sync_context_provider.context_sync(force=True):
            assert lazy_provider.resolve_sync() == Container2.sync_context_provider.resolve_sync()

    with pytest.raises(RuntimeError):
        lazy_provider.resolve_sync()

    with container_context(Container2, scope=ContextScopes.APP):
        assert lazy_provider.resolve_sync() == Container2.sync_context_provider.resolve_sync()

    assert lazy_provider.get_scope() == ContextScopes.APP

    assert lazy_provider.supports_context_sync() is True


async def test_lazy_provider_tear_down_async() -> None:
    lazy_provider = LazyProvider("tests.experimental.test_container_2.Container2.singleton_provider")
    assert lazy_provider.resolve_sync() == Container2.singleton_provider.resolve_sync()

    await lazy_provider.tear_down()

    assert await lazy_provider.resolve() == Container2.singleton_provider.resolve_sync()


def test_lazy_provider_tear_down_sync() -> None:
    lazy_provider = LazyProvider("tests.experimental.test_container_2.Container2.singleton_provider")
    assert lazy_provider.resolve_sync() == Container2.singleton_provider.resolve_sync()

    lazy_provider.tear_down_sync()

    assert lazy_provider.resolve_sync() == Container2.singleton_provider.resolve_sync()


async def test_lazy_provider_not_implemented() -> None:
    lazy_provider = Container2.obj_1
    with pytest.raises(NotImplementedError):
        lazy_provider.get_scope()
    with pytest.raises(NotImplementedError):
        lazy_provider.context_sync()
    with pytest.raises(NotImplementedError):
        lazy_provider.context_async()
    with pytest.raises(NotImplementedError):
        lazy_provider.tear_down_sync()
    with pytest.raises(NotImplementedError):
        await lazy_provider.tear_down()


def test_lazy_provider_attr_getter() -> None:
    lazy_provider = LazyProvider("tests.experimental.test_container_2.Container2.sync_context_provider")
    with lazy_provider.context_sync(force=True):
        assert isinstance(lazy_provider.value.resolve_sync(), float)
