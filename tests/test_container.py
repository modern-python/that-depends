from tests.container import DIContainer
from that_depends import providers


async def test_container_sync_teardown() -> None:
    await DIContainer.init_resources()
    DIContainer.sync_teardown()
    for provider in DIContainer.providers.values():
        if isinstance(provider, providers.Resource | providers.Singleton):
            if provider.is_async:
                assert provider._context.instance is not None
            else:
                assert provider._context.instance is None
