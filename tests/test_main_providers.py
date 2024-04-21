import datetime

import pytest

from tests import container
from tests.container import DIContainer
from that_depends import inject, providers


async def test_main_providers() -> None:
    independent_factory = await DIContainer.independent_factory()
    sync_dependent_factory = await DIContainer.sync_dependent_factory()
    async_dependent_factory = await DIContainer.async_dependent_factory()
    sequence = await DIContainer.sequence()
    singleton1 = await DIContainer.singleton()
    singleton2 = await DIContainer.singleton()
    async_factory = await DIContainer.async_factory()

    assert sync_dependent_factory.independent_factory is not independent_factory
    assert sync_dependent_factory.sync_resource == "sync resource"
    assert async_dependent_factory.async_resource == "async resource"
    assert sequence == ["sync resource", "async resource"]
    assert singleton1 is singleton2
    assert isinstance(async_factory, datetime.datetime)


@inject
async def test_main_providers_overriding() -> None:
    async_resource_mock = "async overriding"
    sync_resource_mock = "sync overriding"
    async_factory_mock = datetime.datetime.now(tz=datetime.UTC)
    independent_factory_mock = container.IndependentFactory(dep1="override", dep2=999)
    singleton_mock = container.SingletonFactory(dep1=False)
    container.DIContainer.async_resource.override(async_resource_mock)
    container.DIContainer.sync_resource.override(sync_resource_mock)
    container.DIContainer.independent_factory.override(independent_factory_mock)
    container.DIContainer.singleton.override(singleton_mock)
    container.DIContainer.async_factory.override(async_factory_mock)

    await container.DIContainer.independent_factory()
    sync_dependent_factory = await container.DIContainer.sync_dependent_factory()
    async_dependent_factory = await container.DIContainer.async_dependent_factory()
    singleton = await container.DIContainer.singleton()
    async_factory = await container.DIContainer.async_factory()

    assert sync_dependent_factory.independent_factory.dep1 == independent_factory_mock.dep1
    assert sync_dependent_factory.independent_factory.dep2 == independent_factory_mock.dep2
    assert sync_dependent_factory.sync_resource == sync_resource_mock
    assert async_dependent_factory.async_resource == async_resource_mock
    assert singleton is singleton_mock
    assert async_factory is async_factory_mock

    container.DIContainer.reset_override()
    assert (await container.DIContainer.async_resource()) == "async resource"


def test_wrong_providers_init() -> None:
    with pytest.raises(RuntimeError, match="Resource must be generator function"):
        providers.Resource(lambda: None)  # type: ignore[arg-type,return-value]

    with pytest.raises(RuntimeError, match="AsyncResource must be async generator function"):
        providers.AsyncResource(lambda: None)  # type: ignore[arg-type,return-value]


def test_container_init_error() -> None:
    with pytest.raises(RuntimeError, match="DIContainer should not be instantiated"):
        DIContainer()
