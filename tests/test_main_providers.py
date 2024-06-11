import datetime

import pytest

from tests import container
from tests.container import DIContainer
from that_depends import providers


async def test_factory_providers() -> None:
    simple_factory = await DIContainer.simple_factory()
    dependent_factory = await DIContainer.dependent_factory()
    async_factory = await DIContainer.async_factory()
    sync_resource = await DIContainer.sync_resource()
    async_resource = await DIContainer.async_resource()

    assert dependent_factory.simple_factory is not simple_factory
    assert DIContainer.simple_factory.sync_resolve() is not simple_factory
    assert dependent_factory.sync_resource == sync_resource
    assert dependent_factory.async_resource == async_resource
    assert isinstance(async_factory, datetime.datetime)


async def test_async_resource_provider() -> None:
    async_resource = await DIContainer.async_resource()

    assert DIContainer.async_resource.sync_resolve() is async_resource


def test_failed_sync_resolve() -> None:
    with pytest.raises(RuntimeError, match="AsyncFactory cannot be resolved synchronously"):
        DIContainer.async_factory.sync_resolve()

    with pytest.raises(RuntimeError, match="AsyncResource cannot be resolved synchronously"):
        DIContainer.async_resource.sync_resolve()

    with pytest.raises(RuntimeError, match="AsyncResource cannot be resolved synchronously"):
        DIContainer.sequence.sync_resolve()


async def test_sync_resolve_after_init() -> None:
    await DIContainer.init_async_resources()
    DIContainer.sequence.sync_resolve()


async def test_list_provider() -> None:
    sequence = await DIContainer.sequence()
    sync_resource = await DIContainer.sync_resource()
    async_resource = await DIContainer.async_resource()

    assert sequence == [sync_resource, async_resource]


async def test_selector_provider_async() -> None:
    container.global_state_for_selector = "async_resource"
    selected = await DIContainer.selector()
    async_resource = await DIContainer.async_resource()

    assert selected == async_resource


async def test_selector_provider_async_missing() -> None:
    container.global_state_for_selector = "missing"
    with pytest.raises(RuntimeError):
        await DIContainer.selector()


async def test_selector_provider_sync() -> None:
    container.global_state_for_selector = "sync_resource"
    selected = DIContainer.selector.sync_resolve()
    sync_resource = DIContainer.sync_resource.sync_resolve()

    assert selected == sync_resource


async def test_selector_provider_sync_missing() -> None:
    container.global_state_for_selector = "missing"
    with pytest.raises(RuntimeError):
        DIContainer.selector.sync_resolve()


async def test_singleton_provider() -> None:
    singleton1 = await DIContainer.singleton()
    singleton2 = await DIContainer.singleton()
    singleton3 = DIContainer.singleton.sync_resolve()
    await DIContainer.singleton.tear_down()
    singleton4 = DIContainer.singleton.sync_resolve()

    assert singleton1 is singleton2 is singleton3
    assert singleton4 is not singleton1


async def test_providers_overriding() -> None:
    async_resource_mock = datetime.datetime.fromisoformat("2023-01-01")
    sync_resource_mock = datetime.datetime.fromisoformat("2024-01-01")
    async_factory_mock = datetime.datetime.fromisoformat("2025-01-01")
    simple_factory_mock = container.SimpleFactory(dep1="override", dep2=999)
    singleton_mock = container.SingletonFactory(dep1=False)
    container.DIContainer.async_resource.override(async_resource_mock)
    container.DIContainer.sync_resource.override(sync_resource_mock)
    container.DIContainer.simple_factory.override(simple_factory_mock)
    container.DIContainer.singleton.override(singleton_mock)
    container.DIContainer.async_factory.override(async_factory_mock)

    await container.DIContainer.simple_factory()
    dependent_factory = await container.DIContainer.dependent_factory()
    singleton = await container.DIContainer.singleton()
    async_factory = await container.DIContainer.async_factory()

    assert dependent_factory.simple_factory.dep1 == simple_factory_mock.dep1
    assert dependent_factory.simple_factory.dep2 == simple_factory_mock.dep2
    assert dependent_factory.sync_resource == sync_resource_mock
    assert dependent_factory.async_resource == async_resource_mock
    assert singleton is singleton_mock
    assert async_factory is async_factory_mock

    container.DIContainer.reset_override()
    assert (await container.DIContainer.async_resource()) != async_resource_mock


async def test_providers_overriding_sync_resolve() -> None:
    async_resource_mock = datetime.datetime.fromisoformat("2023-01-01")
    sync_resource_mock = datetime.datetime.fromisoformat("2024-01-01")
    simple_factory_mock = container.SimpleFactory(dep1="override", dep2=999)
    singleton_mock = container.SingletonFactory(dep1=False)
    container.DIContainer.async_resource.override(async_resource_mock)
    container.DIContainer.sync_resource.override(sync_resource_mock)
    container.DIContainer.simple_factory.override(simple_factory_mock)
    container.DIContainer.singleton.override(singleton_mock)

    container.DIContainer.simple_factory.sync_resolve()
    await container.DIContainer.async_resource.async_resolve()
    dependent_factory = container.DIContainer.dependent_factory.sync_resolve()
    singleton = container.DIContainer.singleton.sync_resolve()

    assert dependent_factory.simple_factory.dep1 == simple_factory_mock.dep1
    assert dependent_factory.simple_factory.dep2 == simple_factory_mock.dep2
    assert dependent_factory.sync_resource == sync_resource_mock
    assert dependent_factory.async_resource == async_resource_mock
    assert singleton is singleton_mock

    container.DIContainer.reset_override()
    assert container.DIContainer.sync_resource.sync_resolve() != sync_resource_mock


def test_wrong_providers_init() -> None:
    with pytest.raises(RuntimeError, match="Resource must be generator function"):
        providers.Resource(lambda: None)  # type: ignore[arg-type,return-value]

    with pytest.raises(RuntimeError, match="AsyncResource must be async generator function"):
        providers.AsyncResource(lambda: None)  # type: ignore[arg-type,return-value]


def test_container_init_error() -> None:
    with pytest.raises(RuntimeError, match="DIContainer should not be instantiated"):
        DIContainer()


async def test_free_dependency() -> None:
    resolver = DIContainer.resolver(container.FreeFactory)
    dep1 = await resolver()
    dep2 = await DIContainer.resolve(container.FreeFactory)
    assert dep1
    assert dep2
