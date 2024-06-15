from tests.container import DIContainer


async def test_list_provider() -> None:
    sequence = await DIContainer.sequence()
    sync_resource = await DIContainer.sync_resource()
    async_resource = await DIContainer.async_resource()

    assert sequence == [sync_resource, async_resource]


async def test_dict_provider() -> None:
    mapping = await DIContainer.mapping()
    sync_resource = await DIContainer.sync_resource()
    async_resource = await DIContainer.async_resource()

    assert mapping == {"sync_resource": sync_resource, "async_resource": async_resource}
    assert mapping == DIContainer.mapping.sync_resolve()
