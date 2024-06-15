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


async def test_singleton_provider() -> None:
    singleton1 = await DIContainer.singleton()
    singleton2 = await DIContainer.singleton()
    singleton3 = DIContainer.singleton.sync_resolve()
    await DIContainer.singleton.tear_down()
    singleton4 = DIContainer.singleton.sync_resolve()

    assert singleton1 is singleton2 is singleton3
    assert singleton4 is not singleton1


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
