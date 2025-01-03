# Resource
- resolve the dependency only once and cache the resolved instance for future injections;
- unlike `Singleton` has finalization logic;
- generator or async generator can be used;
- context manager derived from `typing.ContextManager` or `typing.AsyncContextManager` can be used;

## How it works
```python
import typing

from that_depends import BaseContainer, providers


def create_sync_resource() -> typing.Iterator[str]:
    # resource initialization
    try:
        yield "sync resource"
    finally:
        pass  # resource teardown


async def create_async_resource() -> typing.AsyncIterator[str]:
    # resource initialization
    try:
        yield "async resource"
    finally:
        pass  # resource teardown


class MyContainer(BaseContainer):
    sync_resource = providers.Resource(create_sync_resource)
    async_resource = providers.Resource(create_async_resource)
```

## Concurrency safety
`Resource` is safe to use in threading and asyncio concurrency:
```python
# calling async_resolve concurrently in different coroutines will create only one instance
await MyContainer.async_resource.async_resolve()

# calling sync_resolve concurrently in different threads will create only one instance
MyContainer.sync_resource.sync_resolve()
```
