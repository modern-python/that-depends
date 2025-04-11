import random
import typing

from tests.container import DIContainer
from that_depends import BaseContainer, providers


def _sync_resource() -> typing.Iterator[float]:
    yield random.random()


async def test_container_sync_teardown() -> None:
    await DIContainer.init_resources()
    DIContainer.tear_down_sync()
    for provider in DIContainer.providers.values():
        if isinstance(provider, providers.Resource):
            if provider._is_async:
                assert provider._context.instance is not None
            else:
                assert provider._context.instance is None
        if isinstance(provider, providers.Singleton):
            assert provider._instance is None


async def test_container_tear_down() -> None:
    await DIContainer.init_resources()
    await DIContainer.tear_down()
    for provider in DIContainer.providers.values():
        if isinstance(provider, providers.Resource):
            assert provider._context.instance is None
        if isinstance(provider, providers.Singleton):
            assert provider._instance is None


async def test_container_sync_tear_down_propagation() -> None:
    class _DependentContainer(BaseContainer):
        singleton = providers.Singleton(lambda: random.random())
        resource = providers.Resource(_sync_resource)

    DIContainer.connect_containers(_DependentContainer)

    await DIContainer.init_resources()

    assert isinstance(_DependentContainer.singleton._instance, float)
    assert isinstance(_DependentContainer.resource._context.instance, float)

    DIContainer.tear_down_sync()

    assert _DependentContainer.singleton._instance is None
    assert _DependentContainer.resource._context.instance is None


async def test_container_tear_down_propagation() -> None:
    async def _async_singleton() -> float:
        return random.random()

    async def _async_resource() -> typing.AsyncIterator[float]:
        yield random.random()

    class _DependentContainer(BaseContainer):
        async_singleton = providers.AsyncSingleton(_async_singleton)
        async_resource = providers.Resource(_async_resource)
        sync_singleton = providers.Singleton(lambda: random.random())
        sync_resource = providers.Resource(_sync_resource)

    DIContainer.connect_containers(_DependentContainer)

    await DIContainer.init_resources()

    assert isinstance(_DependentContainer.async_singleton._instance, float)
    assert isinstance(_DependentContainer.async_resource._context.instance, float)
    assert isinstance(_DependentContainer.sync_singleton._instance, float)
    assert isinstance(_DependentContainer.sync_resource._context.instance, float)

    await DIContainer.tear_down()

    assert _DependentContainer.async_singleton._instance is None
    assert _DependentContainer.async_resource._context.instance is None
    assert _DependentContainer.sync_singleton._instance is None
    assert _DependentContainer.sync_resource._context.instance is None
