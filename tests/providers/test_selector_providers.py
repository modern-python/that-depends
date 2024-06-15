import pytest

from tests import container
from tests.container import DIContainer


async def test_selector_provider_async() -> None:
    container.global_state_for_selector = "async_resource"
    selected = await DIContainer.selector()
    async_resource = await DIContainer.async_resource()

    assert selected == async_resource


async def test_selector_provider_async_missing() -> None:
    container.global_state_for_selector = "missing"
    with pytest.raises(RuntimeError):
        await DIContainer.selector()


async def test_selector_provider_sync() -> None:
    container.global_state_for_selector = "sync_resource"
    selected = DIContainer.selector.sync_resolve()
    sync_resource = DIContainer.sync_resource.sync_resolve()

    assert selected == sync_resource


async def test_selector_provider_sync_missing() -> None:
    container.global_state_for_selector = "missing"
    with pytest.raises(RuntimeError):
        DIContainer.selector.sync_resolve()
