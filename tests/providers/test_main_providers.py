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


def test_wrong_providers_init() -> None:
    with pytest.raises(TypeError, match="Unsupported resource type"):
        providers.Resource(lambda: None)  # type: ignore[arg-type,return-value]


def test_container_init_error() -> None:
    with pytest.raises(RuntimeError, match="DIContainer should not be instantiated"):
        DIContainer()


async def test_free_dependency() -> None:
    resolver = DIContainer.resolver(container.FreeFactory)
    dep1 = await resolver()
    dep2 = await DIContainer.resolve(container.FreeFactory)
    assert dep1
    assert dep2
