import datetime

from tests import container
from that_depends import BaseContainer, providers


class DIContainer(BaseContainer):
    sync_resource: providers.Resource[datetime.datetime]
    async_resource: providers.Resource[datetime.datetime]


DIContainer.sync_resource = providers.Resource(container.create_sync_resource)
DIContainer.async_resource = providers.Resource(container.create_async_resource)


async def test_dynamic_container() -> None:
    sync_resource = await DIContainer.sync_resource()
    async_resource = await DIContainer.async_resource()

    assert isinstance(sync_resource, datetime.datetime)
    assert isinstance(async_resource, datetime.datetime)

    await DIContainer.tear_down()
