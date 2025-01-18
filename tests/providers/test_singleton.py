import asyncio
import dataclasses
import random
import threading
import time
import typing
from concurrent.futures import ThreadPoolExecutor, as_completed

import pydantic
import pytest

from that_depends import BaseContainer, providers
from that_depends.providers.singleton import ThreadLocalSingleton


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


async def test_thread_local_singleton_throws_on_async_resolve() -> None:
    with pytest.raises(RuntimeError, match="ThreadLocalSingleton cannot be resolved in an async context."):
        await ThreadLocalSingleton(lambda: None).async_resolve()


async def test_async_singleton_sync_resolve_failure() -> None:
    with pytest.raises(RuntimeError, match="AsyncSingleton cannot be resolved in an sync context."):
        DIContainer.singleton_async.sync_resolve()


def test_thread_local_singleton_same_thread() -> None:
    """Test that the same instance is returned within a single thread."""

    def factory() -> int:
        return random.randint(1, 100)  # noqa: S311

    provider = ThreadLocalSingleton(factory)

    instance1 = provider.sync_resolve()
    instance2 = provider.sync_resolve()

    assert instance1 == instance2, "Singleton failed: Instances within the same thread should be identical."

    provider.tear_down()

    assert provider._instance is None, "Tear down failed: Instance should be reset to None."


def test_thread_local_singleton_different_threads() -> None:
    """Test that different threads receive different instances."""

    def factory() -> int:
        return random.randint(1, 100)  # noqa: S311

    provider = ThreadLocalSingleton(factory)
    results = []

    def resolve_in_thread() -> None:
        results.append(provider.sync_resolve())

    number_of_threads = 10

    threads = [threading.Thread(target=resolve_in_thread) for _ in range(number_of_threads)]

    for thread in threads:
        thread.start()
    for thread in threads:
        thread.join()

    assert len(results) == number_of_threads, "Test failed: Expected results from two threads."
    assert results[0] != results[1], "Thread-local failed: Instances across threads should differ."


def test_thread_local_singleton_override() -> None:
    """Test overriding the ThreadLocalSingleton and resetting the override."""

    def _factory() -> int:
        return random.randint(1, 100)  # noqa: S311

    provider = ThreadLocalSingleton(_factory)

    override_value = 101
    provider.override(override_value)
    instance = provider.sync_resolve()
    assert instance == override_value, "Override failed: Expected overridden value."

    # Reset override and ensure a new instance is created
    provider.reset_override()
    new_instance = provider.sync_resolve()
    assert new_instance != override_value, "Reset override failed: Should no longer return overridden value."


def test_thread_local_singleton_override_in_threads() -> None:
    """Test that resetting the override in one thread does not affect another thread."""

    def _factory() -> int:
        return random.randint(1, 100)  # noqa: S311

    provider = ThreadLocalSingleton(_factory)
    results = {}

    def _thread_task(thread_id: int, override_value: int | None = None) -> None:
        if override_value is not None:
            provider.override(override_value)
        results[thread_id] = provider.sync_resolve()
        if override_value is not None:
            provider.reset_override()

    override_value: typing.Final[int] = 101
    thread1 = threading.Thread(target=_thread_task, args=(1, override_value))
    thread2 = threading.Thread(target=_thread_task, args=(2,))

    thread1.start()
    thread2.start()

    thread1.join()
    thread2.join()

    # Validate results
    assert results[1] == override_value, "Thread 1: Override failed."
    assert results[2] != override_value, "Thread 2: Should not be affected by Thread 1's override."
    assert results[1] != results[2], "Instances should be unique across threads."


def test_thread_local_singleton_override_temporarily() -> None:
    """Test temporarily overriding the ThreadLocalSingleton."""

    def factory() -> int:
        return random.randint(1, 100)  # noqa: S311

    provider = ThreadLocalSingleton(factory)

    override_value: typing.Final = 101
    # Set a temporary override
    with provider.override_context(override_value):
        instance = provider.sync_resolve()
        assert instance == override_value, "Override context failed: Expected overridden value."

    # After the context, reset to the factory
    new_instance = provider.sync_resolve()
    assert new_instance != override_value, "Override context failed: Value should reset after context."
