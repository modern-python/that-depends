import logging
import typing

from that_depends import BaseContainer, providers


logger = logging.getLogger(__name__)


def create_sync_resource() -> typing.Iterator[list[typing.Any]]:
    logger.debug("Resource initiated")
    yield []
    logger.debug("Resource destructed")


async def create_async_resource() -> typing.AsyncIterator[dict[str, typing.Any]]:
    logger.debug("Async resource initiated")
    yield {}
    logger.debug("Async resource destructed")


class TrickyDIContainer(BaseContainer):
    singleton = providers.Singleton(list)
    sync_resource = providers.Resource(create_sync_resource)
    async_resource = providers.Resource(create_async_resource)


async def test_singleton_with_empty_list() -> None:
    singleton1 = await TrickyDIContainer.singleton()
    singleton2 = await TrickyDIContainer.singleton()
    assert singleton1 is singleton2


async def test_resources_with_empty_list() -> None:
    sync_resource1 = await TrickyDIContainer.sync_resource()
    sync_resource2 = await TrickyDIContainer.sync_resource()
    assert sync_resource1 is sync_resource2

    async_resource1 = await TrickyDIContainer.async_resource()
    async_resource2 = await TrickyDIContainer.async_resource()
    assert async_resource1 is async_resource2

    await TrickyDIContainer.tear_down()
