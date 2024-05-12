# AsyncResource
- Same as `Resource` but async generator function is required.
```python
import typing

from that_depends import BaseContainer, providers


async def create_async_resource() -> typing.AsyncIterator[str]:
    # resource initialization
    yield "async resource"
    # resource teardown


class DIContainer(BaseContainer):
    async_resource = providers.AsyncResource(create_async_resource)
```
