from that_depends import BaseContainer, providers


instance = "some string"


class DIContainer(BaseContainer):
    instance = providers.Object(instance)


async def test_object_provider() -> None:
    instance1 = await DIContainer.instance()
    instance2 = DIContainer.instance.sync_resolve()

    assert instance1 is instance2 is instance
