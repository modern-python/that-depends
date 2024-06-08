import datetime

from tests import container
from that_depends import BaseContainer, providers


class InnerContainer(BaseContainer):
    sync_resource = providers.Resource(container.create_sync_resource)
    async_resource = providers.AsyncResource(container.create_async_resource)


class OuterContainer(BaseContainer):
    sequence = providers.List(InnerContainer.sync_resource, InnerContainer.async_resource)


OuterContainer.connect_containers(InnerContainer)


async def test_included_container() -> None:
    sequence = await OuterContainer.sequence()
    assert all(isinstance(x, datetime.datetime) for x in sequence)

    await OuterContainer.tear_down()
    assert InnerContainer.sync_resource._instance is None  # noqa: SLF001
    assert InnerContainer.async_resource._instance is None  # noqa: SLF001

    await OuterContainer.init_async_resources()
    assert InnerContainer.sync_resource._instance is not None  # noqa: SLF001
    assert InnerContainer.async_resource._instance is not None  # noqa: SLF001
    await OuterContainer.tear_down()
