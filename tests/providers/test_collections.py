import typing

import pytest

from tests.container import create_async_resource, create_sync_resource
from that_depends import BaseContainer, providers
from that_depends.providers import AbstractProvider


class DIContainer(BaseContainer):
    sync_resource = providers.Resource(create_sync_resource)
    async_resource = providers.Resource(create_async_resource)
    sequence = providers.List(sync_resource, async_resource)
    mapping = providers.Dict(sync_resource=sync_resource, async_resource=async_resource)


@pytest.fixture(autouse=True)
async def _clear_di_container() -> typing.AsyncIterator[None]:
    try:
        yield
    finally:
        await DIContainer.tear_down()


async def test_list_provider() -> None:
    sequence = await DIContainer.sequence()
    sync_resource = await DIContainer.sync_resource()
    async_resource = await DIContainer.async_resource()

    assert sequence == [sync_resource, async_resource]


def test_list_failed_sync_resolve() -> None:
    with pytest.raises(RuntimeError, match="AsyncResource cannot be resolved synchronously"):
        DIContainer.sequence.sync_resolve()


async def test_list_sync_resolve_after_init() -> None:
    await DIContainer.init_resources()
    DIContainer.sequence.sync_resolve()


async def test_dict_provider() -> None:
    mapping = await DIContainer.mapping()
    sync_resource = await DIContainer.sync_resource()
    async_resource = await DIContainer.async_resource()

    assert mapping == {"sync_resource": sync_resource, "async_resource": async_resource}
    assert mapping == DIContainer.mapping.sync_resolve()


@pytest.mark.parametrize("provider", [DIContainer.sequence, DIContainer.mapping])
async def test_attr_getter_in_collections_providers(provider: AbstractProvider[typing.Any]) -> None:
    with pytest.raises(AttributeError, match=f"'{type(provider)}' object has no attribute 'some_attribute'"):
        await provider.some_attribute
