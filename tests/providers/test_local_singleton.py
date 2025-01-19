import asyncio
import random
import threading
import typing

from that_depends.providers import ThreadLocalSingleton


def _factory() -> int:
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
