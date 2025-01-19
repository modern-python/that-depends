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


async def _async_creator() -> int:
    await asyncio.sleep(0.001)
    return threading.get_ident()


def _sync_creator_with_dependency(dep: int) -> str:
    return f"Singleton {dep}"


class DIContainer(BaseContainer):
    factory: providers.AsyncFactory[int] = providers.AsyncFactory(_async_creator)
    settings: Settings = providers.Singleton(Settings).cast
    singleton = providers.Singleton(SingletonFactory, dep1=settings.some_setting)
    singleton_async = providers.AsyncSingleton(create_async_obj, value=settings.some_setting)
    singleton_with_dependency = providers.Singleton(_sync_creator_with_dependency, dep=factory.cast)


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

    client1, client2 = await asyncio.gather(
        factory_with_resource.async_resolve(), factory_with_resource.async_resolve()
    )

    assert client1 is client2
    assert calls == 1


@pytest.mark.repeat(10)
def test_singleton_threading_concurrency() -> None:
    calls: int = 0
    lock = threading.Lock()

    def create_singleton() -> str:
        nonlocal calls
        with lock:
            calls += 1
        time.sleep(0.01)
        return ""

    singleton = providers.Singleton(create_singleton)

    with ThreadPoolExecutor(max_workers=4) as pool:
        tasks = [
            pool.submit(singleton.sync_resolve),
            pool.submit(singleton.sync_resolve),
            pool.submit(singleton.sync_resolve),
            pool.submit(singleton.sync_resolve),
        ]
        results = [x.result() for x in as_completed(tasks)]

    assert all(x == "" for x in results)
    assert calls == 1


async def test_async_singleton() -> None:
    singleton1 = await DIContainer.singleton_async()
    singleton2 = await DIContainer.singleton_async()
    singleton3 = await DIContainer.singleton_async.async_resolve()
    await DIContainer.singleton_async.tear_down()
    singleton4 = await DIContainer.singleton_async.async_resolve()

    assert singleton1 is singleton2 is singleton3
    assert singleton4 is not singleton1

    await DIContainer.tear_down()


async def test_async_singleton_override() -> None:
    singleton_async = providers.AsyncSingleton(create_async_obj, "foo")
    singleton_async.override(SingletonFactory(dep1="bar"))

    result = await singleton_async.async_resolve()
    assert result == SingletonFactory(dep1="bar")


async def test_async_singleton_asyncio_concurrency() -> None:
    singleton_async = providers.AsyncSingleton(create_async_obj, "foo")

    results = await asyncio.gather(
        singleton_async(),
        singleton_async(),
        singleton_async(),
        singleton_async(),
        singleton_async(),
    )

    assert all(val is results[0] for val in results)


async def test_async_singleton_sync_resolve_failure() -> None:
    with pytest.raises(RuntimeError, match="AsyncSingleton cannot be resolved in an sync context."):
        DIContainer.singleton_async.sync_resolve()


async def test_singleton_async_resolve_with_async_dependencies() -> None:
    expected = await DIContainer.singleton_with_dependency.async_resolve()

    assert expected == await DIContainer.singleton_with_dependency.async_resolve()

    results = await asyncio.gather(*[DIContainer.singleton_with_dependency.async_resolve() for _ in range(10)])

    for val in results:
        assert val == expected

    results = await asyncio.gather(
        *[asyncio.to_thread(DIContainer.singleton_with_dependency.sync_resolve) for _ in range(10)],
    )

    for val in results:
        assert val == expected
