# Resource Provider

A **Resource** is a special provider that:

- **Resolves** its dependency only **once** and **caches** the resolved instance for future injections.
- **Includes** teardown (finalization) logic, unlike a plain `Singleton`.
- **Supports** generator or async generator functions for creation (allowing a `yield` plus teardown in `finally`).
- **Also** allows usage of classes that implement standard Python context managers (`typing.ContextManager` or `typing.AsyncContextManager`), but *does not* automatically integrate with `container_context`.

This makes `Resource` ideal for dependencies that need:

1. A **single creation** step,
2. A **single finalization** step,
3. **Thread/async safety**—all consumers receive the same resource object, and concurrency is handled.

---

## How It Works

### Defining a Sync or Async Resource

You can define your creation logic as either a **generator** or a **context manager** class (sync or async). 

**Synchronous generator** example:

```python
import typing
from that_depends.providers import Resource

def create_sync_resource() -> typing.Iterator[str]:
    print("Creating sync resource")
    try:
        yield "sync resource"
    finally:
        print("Tearing down sync resource")
```

**Asynchronous generator** example:

```python
import typing
from that_depends.providers import Resource

async def create_async_resource() -> typing.AsyncIterator[str]:
    print("Creating async resource")
    try:
        yield "async resource"
    finally:
        print("Tearing down async resource")
```

You then attach them to a container:

```python
from that_depends import BaseContainer

class MyContainer(BaseContainer):
    sync_resource = Resource(create_sync_resource)
    async_resource = Resource(create_async_resource)
```

---

## Resolving and Teardown

Once defined, you can explicitly **resolve** the resource and **tear it down**:

```python
# Synchronous resource usage
value_sync = MyContainer.sync_resource.sync_resolve()
print(value_sync)  # "sync resource"
MyContainer.sync_resource.sync_tear_down()

# Asynchronous resource usage
import asyncio

async def main():
    value_async = await MyContainer.async_resource.async_resolve()
    print(value_async)  # "async resource"
    await MyContainer.async_resource.tear_down()

asyncio.run(main())
```

- **`sync_resolve()`** or **`async_resolve()`**: Creates (if needed) and returns the resource instance.
- **`sync_tear_down()`** or **`tear_down()`**: Closes/cleans up the resource (triggering your `finally` block or exiting the context manager) and resets the cached instance to `None`. A subsequent resolve call will then recreate it.

---

## Concurrency Safety

`Resource` is **safe** to use under **threading** and **asyncio** concurrency. Internally, a lock ensures only one resource instance is created per container:

- Multiple threads calling `sync_resolve()` simultaneously will produce a **single** instance for that container.
- Multiple coroutines calling `async_resolve()` simultaneously will likewise produce **only one** instance for that container in an async environment.

```python
# Even if multiple coroutines call async_resolve in parallel,
# only one instance is created at a time:
await MyContainer.async_resource.async_resolve()

# Similarly, multiple threads calling sync_resolve concurrently
# still yield just one instance until teardown:
MyContainer.sync_resource.sync_resolve()
```

---

## Using Context Managers Directly

If your resource is a standard **context manager** or **async context manager** class, `Resource` will handle entering and exiting it under the hood. For example:

```python
import typing
from that_depends.providers import Resource

class SyncFileManager:
    def __enter__(self) -> str:
        print("Opening file")
        return "/path/to/file"
    def __exit__(self, exc_type, exc_val, exc_tb):
        print("Closing file")

sync_file_resource = Resource(SyncFileManager)

# usage
file_path = sync_file_resource.sync_resolve()
print(file_path)
sync_file_resource.sync_tear_down()
```
