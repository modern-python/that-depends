import datetime

import pytest

from tests import container
from that_depends import BaseContainer, providers


class DIContainer(BaseContainer):
    alias = "dynamic_container"
    sync_resource: providers.Resource[datetime.datetime]


async def test_dynamic_container_not_supported() -> None:
    new_provider = providers.Resource(container.create_sync_resource)
    with pytest.raises(AttributeError):
        DIContainer.sync_resource = new_provider

    with pytest.raises(AttributeError):
        DIContainer.something_new = new_provider
