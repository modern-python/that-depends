import random
import typing
from inspect import signature

from tests.container import DIContainer
from that_depends import BaseContainer, providers
from that_depends.utils import is_set


def _sync_resource() -> typing.Iterator[float]:
    yield random.random()


async def test_container_context_decorator_preserves_callable_metadata() -> None:
    def sync_func(value: int) -> int:
        """Sync documentation."""
        return value

    async def async_func(value: int) -> int:
        """Async documentation."""
        return value

    wrapped_sync = DIContainer.context(sync_func)
    wrapped_async = DIContainer.context(async_func)

    assert wrapped_sync.__name__ == sync_func.__name__
    assert wrapped_sync.__doc__ == sync_func.__doc__
    assert signature(wrapped_sync) == signature(sync_func)
    assert wrapped_sync(1) == 1
    assert wrapped_async.__name__ == async_func.__name__
    assert wrapped_async.__doc__ == async_func.__doc__
    assert signature(wrapped_async) == signature(async_func)
    assert await wrapped_async(1) == 1


async def test_container_sync_teardown() -> None:
    await DIContainer.init_resources()
    DIContainer.tear_down_sync()
    for provider in DIContainer.providers.values():
        if isinstance(provider, providers.Resource):
            if provider._is_async:
                assert is_set(provider._context.instance)
            else:
                assert not is_set(provider._context.instance)
        if isinstance(provider, providers.Singleton):
            assert not is_set(provider._instance)


async def test_container_tear_down() -> None:
    await DIContainer.init_resources()
    await DIContainer.tear_down()
    for provider in DIContainer.providers.values():
        if isinstance(provider, providers.Resource):
            assert not is_set(provider._context.instance)
        if isinstance(provider, providers.Singleton):
            assert not is_set(provider._instance)


async def test_container_sync_tear_down_propagation() -> None:
    class _DependentContainer(BaseContainer):
        singleton = providers.Singleton(random.random)
        resource = providers.Resource(_sync_resource)

    DIContainer.connect_containers(_DependentContainer)

    await DIContainer.init_resources()

    assert isinstance(_DependentContainer.singleton._instance, float)
    assert isinstance(_DependentContainer.resource._context.instance, float)

    DIContainer.tear_down_sync()

    assert not is_set(_DependentContainer.singleton._instance)
    assert not is_set(_DependentContainer.resource._context.instance)


async def test_container_tear_down_propagation() -> None:
    async def _async_singleton() -> float:
        return random.random()

    async def _async_resource() -> typing.AsyncIterator[float]:
        yield random.random()

    class _DependentContainer(BaseContainer):
        async_singleton = providers.AsyncSingleton(_async_singleton)
        async_resource = providers.Resource(_async_resource)
        sync_singleton = providers.Singleton(random.random)
        sync_resource = providers.Resource(_sync_resource)

    DIContainer.connect_containers(_DependentContainer)

    await DIContainer.init_resources()

    assert isinstance(_DependentContainer.async_singleton._instance, float)
    assert isinstance(_DependentContainer.async_resource._context.instance, float)
    assert isinstance(_DependentContainer.sync_singleton._instance, float)
    assert isinstance(_DependentContainer.sync_resource._context.instance, float)

    await DIContainer.tear_down()

    assert not is_set(_DependentContainer.async_singleton._instance)
    assert not is_set(_DependentContainer.async_resource._context.instance)
    assert not is_set(_DependentContainer.sync_singleton._instance)
    assert not is_set(_DependentContainer.sync_resource._context.instance)
