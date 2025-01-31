import asyncio
import random
import threading
import time
import typing
from concurrent.futures.thread import ThreadPoolExecutor

import pytest

from that_depends.providers import AsyncFactory, ThreadLocalSingleton


random.seed(23)


async def _async_factory() -> int:
    await asyncio.sleep(0.01)
    return threading.get_ident()


def _factory() -> int:
    time.sleep(0.01)
    return random.randint(1, 100)  # noqa: S311


def test_thread_local_singleton_same_thread() -> None:
    """Test that the same instance is returned within a single thread."""
    provider = ThreadLocalSingleton(_factory)

    instance1 = provider.sync_resolve()
    instance2 = provider.sync_resolve()

    assert instance1 == instance2, "Singleton failed: Instances within the same thread should be identical."

    provider.tear_down()

    assert provider._instance is None, "Tear down failed: Instance should be reset to None."


def test_thread_local_singleton_different_threads() -> None:
    """Test that different threads receive different instances."""
    provider = ThreadLocalSingleton(_factory)
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
    provider = ThreadLocalSingleton(_factory)

    override_value: typing.Final = 101
    # Set a temporary override
    with provider.override_context(override_value):
        instance = provider.sync_resolve()
        assert instance == override_value, "Override context failed: Expected overridden value."

    # After the context, reset to the factory
    new_instance = provider.sync_resolve()
    assert new_instance != override_value, "Override context failed: Value should reset after context."


async def test_async_thread_local_singleton_asyncio_concurrency() -> None:
    singleton_async = ThreadLocalSingleton(_factory)

    expected = await singleton_async.async_resolve()

    results = await asyncio.gather(
        singleton_async(),
        singleton_async(),
        singleton_async(),
        singleton_async(),
        singleton_async(),
    )

    assert all(val is results[0] for val in results)
    for val in results:
        assert val == expected, "Instances should be identical across threads."


async def test_thread_local_singleton_async_resolve_with_async_dependencies() -> None:
    async_provider = AsyncFactory(_async_factory)

    def _dependent_creator(v: int) -> int:
        return v

    provider = ThreadLocalSingleton(_dependent_creator, v=async_provider.cast)

    expected = await provider.async_resolve()

    assert expected == await provider.async_resolve()

    results = await asyncio.gather(*[provider.async_resolve() for _ in range(10)])

    for val in results:
        assert val == expected, "Instances should be identical across threads."
    with pytest.raises(RuntimeError):
        # This should raise an error because the provider is async and resolution is attempted.
        await asyncio.gather(asyncio.to_thread(provider.sync_resolve))

    def _run_async_in_thread(coroutine: typing.Awaitable[typing.Any]) -> typing.Any:  # noqa: ANN401
        loop = asyncio.new_event_loop()
        asyncio.set_event_loop(loop)
        result = loop.run_until_complete(coroutine)
        loop.close()
        return result

    with ThreadPoolExecutor() as executor:
        future = executor.submit(_run_async_in_thread, provider.async_resolve())

        result = future.result()

        assert result != expected, (
            "Since singleton should have been newly resolved, it should not have the same thread id."
        )


async def test_thread_local_singleton_async_resolve_override() -> None:
    provider = ThreadLocalSingleton(_factory)

    override_value = 101

    provider.override(override_value)

    assert await provider.async_resolve() == override_value, "Override failed: Expected overridden value."
