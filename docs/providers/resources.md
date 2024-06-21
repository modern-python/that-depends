# Resources
Resources are initialized only once and have teardown logic.
There are `Resource` and `AsyncResource`

## Resource
- Generator function is required.
```python
import typing

from that_depends import BaseContainer, providers


def create_sync_resource() -> typing.Iterator[str]:
    # resource initialization
    try:
        yield "sync resource"
    finally:
        pass  # resource teardown

class DIContainer(BaseContainer):
    sync_resource = providers.Resource(create_sync_resource)
```

## AsyncResource
- Async generator function is required.
```python
import typing

from that_depends import BaseContainer, providers


async def create_async_resource() -> typing.AsyncIterator[str]:
    # resource initialization
    try:
        yield "async resource"
    finally:
        pass  # resource teardown


class DIContainer(BaseContainer):
    async_resource = providers.AsyncResource(create_async_resource)
```
