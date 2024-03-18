import pytest

from tests import container
from that_depends import inject


@pytest.mark.asyncio()
@inject
async def test_overriding() -> None:
    async_resource_mock = "async overriding"
    sync_resource_mock = "sync overriding"
    independent_factory_mock = container.IndependentFactory(dep1="override", dep2=999)
    container.DIContainer.async_resource.override(async_resource_mock)
    container.DIContainer.sync_resource.override(sync_resource_mock)
    container.DIContainer.independent_factory.override(independent_factory_mock)

    await container.DIContainer.independent_factory()
    sync_dependent_factory = await container.DIContainer.sync_dependent_factory()
    async_dependent_factory = await container.DIContainer.async_dependent_factory()
    assert sync_dependent_factory.independent_factory.dep1 == independent_factory_mock.dep1
    assert sync_dependent_factory.independent_factory.dep2 == independent_factory_mock.dep2
    assert sync_dependent_factory.sync_resource == sync_resource_mock
    assert async_dependent_factory.async_resource == async_resource_mock

    container.DIContainer.reset_override()
    assert (await container.DIContainer.async_resource()) == "async resource"
