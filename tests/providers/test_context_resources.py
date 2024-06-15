import datetime
import logging
import typing

import pytest

from that_depends import BaseContainer, inject, providers
from that_depends.providers import container_context


logger = logging.getLogger(__name__)


def create_sync_context_resource() -> typing.Iterator[datetime.datetime]:
    logger.debug("Resource initiated")
    yield datetime.datetime.now(tz=datetime.timezone.utc)
    logger.debug("Resource destructed")


async def create_async_context_resource() -> typing.AsyncIterator[datetime.datetime]:
    logger.debug("Async resource initiated")
    yield datetime.datetime.now(tz=datetime.timezone.utc)
    logger.debug("Async resource destructed")


class DIContainer(BaseContainer):
    sync_context_resource = providers.ContextResource(create_sync_context_resource)
    async_context_resource = providers.AsyncContextResource(create_async_context_resource)


@pytest.fixture(params=[DIContainer.sync_context_resource, DIContainer.async_context_resource])
def context_resource(request: pytest.FixtureRequest) -> providers.AbstractResource[typing.Any]:
    return typing.cast(providers.AbstractResource[typing.Any], request.param)


async def test_context_resource_without_context_init(
    context_resource: providers.AbstractResource[datetime.datetime],
) -> None:
    with pytest.raises(RuntimeError, match="Context is not set. Use container_context"):
        await context_resource.async_resolve()

    with pytest.raises(RuntimeError, match="Context is not set. Use container_context"):
        context_resource.sync_resolve()


@container_context()
async def test_context_resource(context_resource: providers.AbstractResource[datetime.datetime]) -> None:
    context_resource_result = await context_resource()

    assert await context_resource() is context_resource_result


async def test_context_resource_different_context(
    context_resource: providers.AbstractResource[datetime.datetime],
) -> None:
    async with container_context():
        context_resource_instance1 = await context_resource()

    async with container_context():
        context_resource_instance2 = await context_resource()

    assert context_resource_instance1 is not context_resource_instance2


async def test_context_resource_included_context(
    context_resource: providers.AbstractResource[datetime.datetime],
) -> None:
    async with container_context():
        context_resource_instance1 = await context_resource()
        async with container_context():
            context_resource_instance2 = await context_resource()

        context_resource_instance3 = await context_resource()

    assert context_resource_instance1 is not context_resource_instance2
    assert context_resource_instance1 is context_resource_instance3


@inject
async def test_context_resources_overriding(context_resource: providers.AbstractResource[datetime.datetime]) -> None:
    context_resource_mock = datetime.datetime.now(tz=datetime.timezone.utc)
    context_resource.override(context_resource_mock)

    context_resource_result = await context_resource()
    context_resource_result2 = context_resource.sync_resolve()
    assert context_resource_result is context_resource_result2 is context_resource_mock

    DIContainer.reset_override()
    with pytest.raises(RuntimeError, match="Context is not set. Use container_context"):
        await context_resource()


def test_context_resources_wrong_providers_init() -> None:
    with pytest.raises(RuntimeError, match="ContextResource must be generator function"):
        providers.ContextResource(lambda: None)  # type: ignore[arg-type,return-value]

    with pytest.raises(RuntimeError, match="AsyncContextResource must be async generator function"):
        providers.AsyncContextResource(lambda: None)  # type: ignore[arg-type,return-value]
