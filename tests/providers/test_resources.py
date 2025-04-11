import asyncio
import logging
import threading
import time
import typing
from concurrent.futures import ThreadPoolExecutor, as_completed

import pytest

from tests.creators import (
    AsyncContextManagerResource,
    ContextManagerResource,
    create_async_resource,
    create_sync_resource,
)
from that_depends import BaseContainer, providers


logger = logging.getLogger(__name__)


class DIContainer(BaseContainer):
    alias = "resources_container"
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
    async_resource1 = await DIContainer.async_resource.resolve()
    async_resource2 = DIContainer.async_resource.resolve_sync()
    assert async_resource1 is async_resource2


async def test_async_resource_from_class() -> None:
    async_resource1 = await DIContainer.async_resource_from_class.resolve()
    async_resource2 = DIContainer.async_resource_from_class.resolve_sync()
    assert async_resource1 is async_resource2


async def test_sync_resource() -> None:
    sync_resource1 = await DIContainer.sync_resource.resolve()
    sync_resource2 = await DIContainer.sync_resource.resolve()
    assert sync_resource1 is sync_resource2


async def test_sync_resource_from_class() -> None:
    sync_resource1 = await DIContainer.sync_resource_from_class.resolve()
    sync_resource2 = await DIContainer.sync_resource_from_class.resolve()
    assert sync_resource1 is sync_resource2


async def test_async_resource_overridden() -> None:
    async_resource1 = await DIContainer.sync_resource.resolve()

    DIContainer.sync_resource.override_sync("override")

    async_resource2 = DIContainer.sync_resource.resolve_sync()
    async_resource3 = await DIContainer.sync_resource.resolve()

    DIContainer.sync_resource.reset_override_sync()

    async_resource4 = DIContainer.sync_resource.resolve_sync()

    assert async_resource2 is not async_resource1
    assert async_resource2 is async_resource3
    assert async_resource4 is async_resource1


async def test_sync_resource_overridden() -> None:
    sync_resource1 = await DIContainer.sync_resource.resolve()

    DIContainer.sync_resource.override_sync("override")

    sync_resource2 = DIContainer.sync_resource.resolve_sync()
    sync_resource3 = await DIContainer.sync_resource.resolve()

    DIContainer.sync_resource.reset_override_sync()

    sync_resource4 = DIContainer.sync_resource.resolve_sync()

    assert sync_resource2 is not sync_resource1
    assert sync_resource2 is sync_resource3
    assert sync_resource4 is sync_resource1


async def test_resource_with_empty_list() -> None:
    def create_sync_resource_with_list() -> typing.Iterator[list[typing.Any]]:
        logger.debug("Resource initiated")
        yield []
        logger.debug("Resource destructed")

    async def create_async_resource_with_dict() -> typing.AsyncIterator[dict[str, typing.Any]]:
        logger.debug("Async resource initiated")
        yield {}
        logger.debug("Async resource destructed")

    sync_resource = providers.Resource(create_sync_resource_with_list)
    async_resource = providers.Resource(create_async_resource_with_dict)

    sync_resource1 = await sync_resource()
    sync_resource2 = await sync_resource()
    assert sync_resource1 is sync_resource2

    async_resource1 = await async_resource()
    async_resource2 = await async_resource()
    assert async_resource1 is async_resource2

    await sync_resource.tear_down()
    await async_resource.tear_down()


async def test_resource_unsupported_creator() -> None:
    with pytest.raises(TypeError, match="Unsupported resource type"):
        providers.Resource(None)  # type: ignore[arg-type]


@pytest.mark.repeat(10)
async def test_async_resource_asyncio_concurrency() -> None:
    calls: int = 0

    async def create_resource() -> typing.AsyncIterator[str]:
        nonlocal calls
        calls += 1
        await asyncio.sleep(0)
        yield ""

    resource = providers.Resource(create_resource)

    await asyncio.gather(resource.resolve(), resource.resolve())

    assert calls == 1


@pytest.mark.repeat(10)
async def test_async_resource_async_teardown() -> None:
    calls: int = 0

    async def _create_resource() -> typing.AsyncIterator[str]:
        yield ""
        nonlocal calls
        await asyncio.sleep(0.01)
        calls += 1

    resource = providers.Resource(_create_resource)

    await resource.resolve()

    await asyncio.gather(*[resource.tear_down() for _ in range(10)])

    assert calls == 1


@pytest.mark.repeat(10)
def test_resource_threading_concurrency() -> None:
    calls: int = 0
    lock = threading.Lock()

    def create_resource() -> typing.Iterator[str]:
        nonlocal calls
        with lock:
            calls += 1
        time.sleep(0.01)
        yield ""

    resource = providers.Resource(create_resource)

    with ThreadPoolExecutor(max_workers=4) as pool:
        tasks = [
            pool.submit(resource.resolve_sync),
            pool.submit(resource.resolve_sync),
            pool.submit(resource.resolve_sync),
            pool.submit(resource.resolve_sync),
        ]
        results = [x.result() for x in as_completed(tasks)]

    assert results == ["", "", "", ""]
    assert calls == 1


def test_sync_resource_sync_tear_down() -> None:
    DIContainer.sync_resource.resolve_sync()
    assert DIContainer.sync_resource._context.instance is not None
    DIContainer.sync_resource.tear_down_sync()
    assert DIContainer.sync_resource._context.instance is None


async def test_async_resource_sync_tear_down_raises() -> None:
    await DIContainer.async_resource.resolve()
    assert DIContainer.async_resource._context.instance is not None
    with pytest.raises(RuntimeError):
        DIContainer.async_resource.tear_down_sync()
