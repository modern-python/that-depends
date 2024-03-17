import pytest

from tests import container
from that_depends import inject


@pytest.mark.asyncio()
@inject
async def test_overriding() -> None:
    container.DIContainer.async_resource.override("async overriding")
    container.DIContainer.sync_resource.override("sync overriding")
    container.DIContainer.independent_factory.override(container.IndependentFactory(dep1="override", dep2=0))

    await container.DIContainer.independent_factory()
    sync_dependent_factory = await container.DIContainer.sync_dependent_factory()
    async_dependent_factory = await container.DIContainer.async_dependent_factory()
    assert sync_dependent_factory.independent_factory.dep1 == "override"
    assert sync_dependent_factory.independent_factory.dep2 == 0
    assert sync_dependent_factory.sync_resource == "sync overriding"
    assert async_dependent_factory.async_resource == "async overriding"

    container.DIContainer.reset_override()
    assert (await container.DIContainer.async_resource()) == "async resource"
