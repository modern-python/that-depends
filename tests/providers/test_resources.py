import asyncio
import typing

import pytest

from tests.creators import (
    AsyncContextManagerResource,
    ContextManagerResource,
    create_async_resource,
    create_sync_resource,
)
from that_depends import BaseContainer, providers


class DIContainer(BaseContainer):
    async_resource = providers.Resource(create_async_resource)
    sync_resource = providers.Resource(create_sync_resource)
    async_resource_from_class = providers.Resource(AsyncContextManagerResource)
    sync_resource_from_class = providers.Resource(ContextManagerResource)


@pytest.fixture(autouse=True)
async def _tear_down() -> typing.AsyncIterator[None]:
    try:
        yield
    finally:
        await DIContainer.tear_down()


async def test_async_resource() -> None:
    async_resource1 = await DIContainer.async_resource.async_resolve()
    async_resource2 = DIContainer.async_resource.sync_resolve()
    assert async_resource1 is async_resource2


async def test_async_resource_from_class() -> None:
    async_resource1 = await DIContainer.async_resource_from_class.async_resolve()
    async_resource2 = DIContainer.async_resource_from_class.sync_resolve()
    assert async_resource1 is async_resource2


async def test_sync_resource() -> None:
    sync_resource1 = await DIContainer.sync_resource.async_resolve()
    sync_resource2 = await DIContainer.sync_resource.async_resolve()
    assert sync_resource1 is sync_resource2


async def test_sync_resource_from_class() -> None:
    sync_resource1 = await DIContainer.sync_resource_from_class.async_resolve()
    sync_resource2 = await DIContainer.sync_resource_from_class.async_resolve()
    assert sync_resource1 is sync_resource2


async def test_async_resource_overridden() -> None:
    async_resource1 = await DIContainer.sync_resource.async_resolve()

    DIContainer.sync_resource.override("override")

    async_resource2 = DIContainer.sync_resource.sync_resolve()
    async_resource3 = await DIContainer.sync_resource.async_resolve()

    DIContainer.sync_resource.reset_override()

    async_resource4 = DIContainer.sync_resource.sync_resolve()

    assert async_resource2 is not async_resource1
    assert async_resource2 is async_resource3
    assert async_resource4 is async_resource1


async def test_sync_resource_overridden() -> None:
    sync_resource1 = await DIContainer.sync_resource.async_resolve()

    DIContainer.sync_resource.override("override")

    sync_resource2 = DIContainer.sync_resource.sync_resolve()
    sync_resource3 = await DIContainer.sync_resource.async_resolve()

    DIContainer.sync_resource.reset_override()

    sync_resource4 = DIContainer.sync_resource.sync_resolve()

    assert sync_resource2 is not sync_resource1
    assert sync_resource2 is sync_resource3
    assert sync_resource4 is sync_resource1


async def test_async_resource_race_condition() -> None:
    calls: int = 0

    async def create_resource() -> typing.AsyncIterator[str]:
        nonlocal calls
        calls += 1
        await asyncio.sleep(0)
        yield ""

    resource = providers.Resource(create_resource)

    async def resolve_resource() -> str:
        return await resource.async_resolve()

    await asyncio.gather(resolve_resource(), resolve_resource())

    assert calls == 1


async def test_resource_unsupported_creator() -> None:
    with pytest.raises(TypeError, match="Unsupported resource type"):
        providers.Resource(None)  # type: ignore[arg-type]
