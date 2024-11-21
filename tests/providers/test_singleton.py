import asyncio
import dataclasses
import threading
import time
import typing
from concurrent.futures import ThreadPoolExecutor, as_completed

import pydantic
import pytest

from that_depends import BaseContainer, providers


@dataclasses.dataclass(frozen=True, kw_only=True, slots=True)
class SingletonFactory:
    dep1: str


class Settings(pydantic.BaseModel):
    some_setting: str = "some_value"
    other_setting: str = "other_value"


async def create_async_obj(value: str) -> SingletonFactory:
    await asyncio.sleep(0.001)
    return SingletonFactory(dep1=f"async {value}")


class DIContainer(BaseContainer):
    settings: Settings = providers.Singleton(Settings).cast
    singleton = providers.Singleton(SingletonFactory, dep1=settings.some_setting)
    singleton_async = providers.AsyncSingleton(create_async_obj, value=settings.some_setting)


async def test_singleton_provider() -> None:
    singleton1 = await DIContainer.singleton()
    singleton2 = await DIContainer.singleton()
    singleton3 = DIContainer.singleton.sync_resolve()
    await DIContainer.singleton.tear_down()
    singleton4 = DIContainer.singleton.sync_resolve()

    assert singleton1 is singleton2 is singleton3
    assert singleton4 is not singleton1

    await DIContainer.tear_down()


async def test_singleton_async_provider() -> None:
    singleton1 = await DIContainer.singleton_async()
    singleton2 = await DIContainer.singleton_async()
    singleton3 = await DIContainer.singleton_async.async_resolve()
    await DIContainer.singleton_async.tear_down()
    singleton4 = await DIContainer.singleton_async.async_resolve()

    assert singleton1 is singleton2 is singleton3
    assert singleton4 is not singleton1

    await DIContainer.tear_down()


async def test_singleton_async_provider_override() -> None:
    singleton_async = providers.AsyncSingleton(create_async_obj, "foo")
    singleton_async.override(SingletonFactory(dep1="bar"))

    result = await singleton_async.async_resolve()
    assert result == SingletonFactory(dep1="bar")


async def test_singleton_async_provider_concurrent() -> None:
    singleton_async = providers.AsyncSingleton(create_async_obj, "foo")

    results = await asyncio.gather(
        singleton_async(),
        singleton_async(),
        singleton_async(),
        singleton_async(),
        singleton_async(),
    )

    assert set(results) == {results[0]}


async def test_singleton_async_provider_sync_resolve() -> None:
    with pytest.raises(RuntimeError, match="AsyncSingleton cannot be resolved in an sync context."):
        DIContainer.singleton_async.sync_resolve()


async def test_singleton_attr_getter() -> None:
    singleton1 = await DIContainer.singleton()

    assert singleton1.dep1 == Settings().some_setting

    await DIContainer.tear_down()


async def test_singleton_with_empty_list() -> None:
    singleton = providers.Singleton(list[object])

    singleton1 = await singleton()
    singleton2 = await singleton()
    assert singleton1 is singleton2


@pytest.mark.repeat(10)
async def test_singleton_asyncio_concurrency() -> None:
    calls: int = 0

    async def create_resource() -> typing.AsyncIterator[str]:
        nonlocal calls
        calls += 1
        await asyncio.sleep(0)
        yield ""

    @dataclasses.dataclass(kw_only=True, slots=True)
    class SimpleCreator:
        dep1: str

    resource = providers.Resource(create_resource)
    factory_with_resource = providers.Singleton(SimpleCreator, dep1=resource.cast)

    async def resolve_factory() -> SimpleCreator:
        return await factory_with_resource.async_resolve()

    client1, client2 = await asyncio.gather(resolve_factory(), resolve_factory())

    assert client1 is client2
    assert calls == 1


@pytest.mark.repeat(10)
def test_singleton_sync_resolve_concurrency() -> None:
    calls: int = 0
    lock = threading.Lock()

    def create_singleton() -> str:
        nonlocal calls
        with lock:
            calls += 1
        time.sleep(0.01)
        return ""

    singleton = providers.Singleton(create_singleton)

    def resolve_singleton() -> str:
        return singleton.sync_resolve()

    with ThreadPoolExecutor(max_workers=4) as pool:
        tasks = [
            pool.submit(resolve_singleton),
            pool.submit(resolve_singleton),
            pool.submit(resolve_singleton),
            pool.submit(resolve_singleton),
        ]
        results = [x.result() for x in as_completed(tasks)]

    assert all(x == "" for x in results)
    assert calls == 1
