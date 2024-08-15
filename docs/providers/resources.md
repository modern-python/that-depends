# Resource
- Resources are initialized only once and have teardown logic.
- Generator or async generator is required.
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


class DIContainer(BaseContainer):
    sync_resource = providers.Resource(create_sync_resource)
    async_resource = providers.Resource(create_async_resource)
```
