import asyncio
import dataclasses
import threading
import time
import typing
from concurrent.futures import ThreadPoolExecutor, as_completed

import pydantic
import pytest

from that_depends import BaseContainer, providers


@dataclasses.dataclass(kw_only=True, slots=True)
class SingletonFactory:
    dep1: str


class Settings(pydantic.BaseModel):
    some_setting: str = "some_value"
    other_setting: str = "other_value"


class DIContainer(BaseContainer):
    settings: Settings = providers.Singleton(Settings).cast
    singleton = providers.Singleton(SingletonFactory, dep1=settings.some_setting)


async def test_singleton_provider() -> None:
    singleton1 = await DIContainer.singleton()
    singleton2 = await DIContainer.singleton()
    singleton3 = DIContainer.singleton.sync_resolve()
    await DIContainer.singleton.tear_down()
    singleton4 = DIContainer.singleton.sync_resolve()

    assert singleton1 is singleton2 is singleton3
    assert singleton4 is not singleton1

    await DIContainer.tear_down()


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
