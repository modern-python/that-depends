import datetime

from tests import container
from that_depends import BaseContainer, providers


class InnerContainer(BaseContainer):
    sync_resource = providers.Resource(container.create_sync_resource)
    async_resource = providers.Resource(container.create_async_resource)


class OuterContainer(BaseContainer):
    sequence = providers.List(InnerContainer.sync_resource, InnerContainer.async_resource)


OuterContainer.connect_containers(InnerContainer)


async def test_included_container() -> None:
    sequence = await OuterContainer.sequence()
    assert all(isinstance(x, datetime.datetime) for x in sequence)

    await OuterContainer.tear_down()
    assert InnerContainer.sync_resource._context.instance is None
    assert InnerContainer.async_resource._context.instance is None

    await OuterContainer.init_resources()
    sync_resource_context = InnerContainer.sync_resource._context
    assert sync_resource_context
    assert sync_resource_context.instance is not None
    async_resource_context = InnerContainer.async_resource._context
    assert async_resource_context
    assert async_resource_context.instance is not None
    await OuterContainer.tear_down()
