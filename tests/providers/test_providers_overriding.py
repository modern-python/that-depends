import datetime
import typing

import pytest

from tests import container
from that_depends import BaseContainer, providers
from that_depends.providers.mixin import CannotTearDownSyncError


async def test_batch_providers_overriding() -> None:
    async_resource_mock = datetime.datetime.fromisoformat("2023-01-01")
    sync_resource_mock = datetime.datetime.fromisoformat("2024-01-01")
    async_factory_mock = datetime.datetime.fromisoformat("2025-01-01")
    simple_factory_mock = container.SimpleFactory(dep1="override", dep2=999)
    singleton_mock = container.SingletonFactory(dep1=False)
    object_mock = object()

    providers_for_overriding = {
        "async_resource": async_resource_mock,
        "sync_resource": sync_resource_mock,
        "simple_factory": simple_factory_mock,
        "singleton": singleton_mock,
        "async_factory": async_factory_mock,
        "object": object_mock,
    }

    with container.DIContainer.override_providers_sync(providers_for_overriding):
        await container.DIContainer.simple_factory()
        dependent_factory = await container.DIContainer.dependent_factory()
        singleton = await container.DIContainer.singleton()
        async_factory = await container.DIContainer.async_factory()
        obj = await container.DIContainer.object()

    assert dependent_factory.simple_factory.dep1 == simple_factory_mock.dep1
    assert dependent_factory.simple_factory.dep2 == simple_factory_mock.dep2
    assert dependent_factory.sync_resource == sync_resource_mock
    assert dependent_factory.async_resource == async_resource_mock
    assert singleton is singleton_mock
    assert async_factory is async_factory_mock
    assert obj is object_mock

    assert (await container.DIContainer.async_resource()) != async_resource_mock


async def test_batch_providers_overriding_sync_resolve() -> None:
    async_resource_mock = datetime.datetime.fromisoformat("2023-01-01")
    sync_resource_mock = datetime.datetime.fromisoformat("2024-01-01")
    simple_factory_mock = container.SimpleFactory(dep1="override", dep2=999)
    singleton_mock = container.SingletonFactory(dep1=False)
    object_mock = object()

    providers_for_overriding = {
        "async_resource": async_resource_mock,
        "sync_resource": sync_resource_mock,
        "simple_factory": simple_factory_mock,
        "singleton": singleton_mock,
        "object": object_mock,
    }

    with container.DIContainer.override_providers_sync(providers_for_overriding):
        container.DIContainer.simple_factory.resolve_sync()
        await container.DIContainer.async_resource.resolve()
        dependent_factory = container.DIContainer.dependent_factory.resolve_sync()
        singleton = container.DIContainer.singleton.resolve_sync()
        obj = container.DIContainer.object.resolve_sync()

    assert dependent_factory.simple_factory.dep1 == simple_factory_mock.dep1
    assert dependent_factory.simple_factory.dep2 == simple_factory_mock.dep2
    assert dependent_factory.sync_resource == sync_resource_mock
    assert dependent_factory.async_resource == async_resource_mock
    assert singleton is singleton_mock
    assert obj is object_mock

    assert container.DIContainer.sync_resource.resolve_sync() != sync_resource_mock


def test_providers_overriding_with_context_manager() -> None:
    simple_factory_mock = container.SimpleFactory(dep1="override", dep2=999)

    with container.DIContainer.simple_factory.override_context_sync(simple_factory_mock):
        assert container.DIContainer.simple_factory.resolve_sync() is simple_factory_mock

    assert container.DIContainer.simple_factory.resolve_sync() is not simple_factory_mock


async def test_providers_overriding_with_async_context_manager() -> None:
    simple_factory_mock = container.SimpleFactory(dep1="override", dep2=999)

    async with container.DIContainer.simple_factory.override_context(simple_factory_mock):
        assert container.DIContainer.simple_factory.resolve_sync() is simple_factory_mock

    assert container.DIContainer.simple_factory.resolve_sync() is not simple_factory_mock


def test_providers_overriding_fail_with_unknown_provider() -> None:
    unknown_provider_name = "unknown_provider_name"
    match = f"Provider with name {unknown_provider_name!r} not found"
    providers_for_overriding = {unknown_provider_name: None}

    with (
        pytest.raises(RuntimeError, match=match),
        container.DIContainer.override_providers_sync(providers_for_overriding),
    ):
        ...  # pragma: no cover


async def test_providers_overriding() -> None:
    async_resource_mock = datetime.datetime.fromisoformat("2023-01-01")
    sync_resource_mock = datetime.datetime.fromisoformat("2024-01-01")
    async_factory_mock = datetime.datetime.fromisoformat("2025-01-01")
    simple_factory_mock = container.SimpleFactory(dep1="override", dep2=999)
    singleton_mock = container.SingletonFactory(dep1=False)
    object_mock = object()
    container.DIContainer.async_resource.override_sync(async_resource_mock)
    container.DIContainer.sync_resource.override_sync(sync_resource_mock)
    container.DIContainer.simple_factory.override_sync(simple_factory_mock)
    container.DIContainer.singleton.override_sync(singleton_mock)
    container.DIContainer.async_factory.override_sync(async_factory_mock)
    container.DIContainer.object.override_sync(object_mock)

    await container.DIContainer.simple_factory()
    dependent_factory = await container.DIContainer.dependent_factory()
    singleton = await container.DIContainer.singleton()
    async_factory = await container.DIContainer.async_factory()
    obj = await container.DIContainer.object()

    assert dependent_factory.simple_factory.dep1 == simple_factory_mock.dep1
    assert dependent_factory.simple_factory.dep2 == simple_factory_mock.dep2
    assert dependent_factory.sync_resource == sync_resource_mock
    assert dependent_factory.async_resource == async_resource_mock
    assert singleton is singleton_mock
    assert async_factory is async_factory_mock
    assert obj is object_mock

    container.DIContainer.reset_override_sync()
    assert (await container.DIContainer.async_resource()) != async_resource_mock


async def test_providers_overriding_sync_resolve() -> None:
    async_resource_mock = datetime.datetime.fromisoformat("2023-01-01")
    sync_resource_mock = datetime.datetime.fromisoformat("2024-01-01")
    simple_factory_mock = container.SimpleFactory(dep1="override", dep2=999)
    singleton_mock = container.SingletonFactory(dep1=False)
    object_mock = object()
    container.DIContainer.async_resource.override_sync(async_resource_mock)
    container.DIContainer.sync_resource.override_sync(sync_resource_mock)
    container.DIContainer.simple_factory.override_sync(simple_factory_mock)
    container.DIContainer.singleton.override_sync(singleton_mock)
    container.DIContainer.object.override_sync(object_mock)

    container.DIContainer.simple_factory.resolve_sync()
    await container.DIContainer.async_resource.resolve()
    dependent_factory = container.DIContainer.dependent_factory.resolve_sync()
    singleton = container.DIContainer.singleton.resolve_sync()
    obj = container.DIContainer.object.resolve_sync()

    assert dependent_factory.simple_factory.dep1 == simple_factory_mock.dep1
    assert dependent_factory.simple_factory.dep2 == simple_factory_mock.dep2
    assert dependent_factory.sync_resource == sync_resource_mock
    assert dependent_factory.async_resource == async_resource_mock
    assert singleton is singleton_mock
    assert obj is object_mock

    container.DIContainer.reset_override_sync()
    assert container.DIContainer.sync_resource.resolve_sync() != sync_resource_mock


async def test_provider_tear_down_after_override() -> None:
    original_value = 100
    override_value = 32

    class _MyContainer(BaseContainer):
        B = providers.Singleton(lambda: original_value)
        A = providers.Singleton(lambda x: x, B)

    a_old = await _MyContainer.A.resolve()

    _MyContainer.B.override_sync(override_value, tear_down_children=True)

    a_new = await _MyContainer.A()

    assert a_old != a_new

    _MyContainer.B.reset_override_sync(tear_down_children=True)

    assert original_value == _MyContainer.B.resolve_sync()


async def test_provider_tear_down_after_async_override() -> None:
    original_value = 100
    override_value = 32

    class _MyContainer(BaseContainer):
        B = providers.Singleton(lambda: original_value)
        A = providers.Singleton(lambda x: x, B)

    a_old = await _MyContainer.A.resolve()

    await _MyContainer.B.override(override_value, tear_down_children=True)

    a_new = await _MyContainer.A()

    assert a_old != a_new

    await _MyContainer.B.reset_override(tear_down_children=True)

    assert original_value == _MyContainer.B.resolve_sync()


async def test_provider_sync_override_raises_on_async_teardown() -> None:
    original_value = 100

    async def _async_creator(x: int) -> typing.AsyncIterator[int]:
        yield x

    class _MyContainer(BaseContainer):
        B = providers.Singleton(lambda: original_value)
        A = providers.Resource(_async_creator, B.cast)

    await _MyContainer.A.resolve()
    with pytest.raises(CannotTearDownSyncError):
        _MyContainer.B.override_sync(20, tear_down_children=True, raise_on_async=True)

    with pytest.warns(RuntimeWarning):
        _MyContainer.B.override_sync(20, tear_down_children=True, raise_on_async=False)
