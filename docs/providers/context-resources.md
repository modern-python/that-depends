# Context resources
Context resources are resources with scoped lifecycle.
There are `ContextResource` and `AsyncContextResource`

## ContextResource
- Generator function is required.
```python
import typing

import pytest

from that_depends import BaseContainer, providers, container_context


def create_sync_resource() -> typing.Iterator[str]:
    # resource initialization
    try:
        yield "sync resource"
    finally:
        pass  # resource teardown

class DIContainer(BaseContainer):
    context_resource = providers.ContextResource(create_sync_resource)


async def main() -> None:
    async with container_context():
        # context resource can be resolved only inside of context
        DIContainer.context_resource.sync_resolve()
    
    # outside the context resolving will fail
    with pytest.raises(RuntimeError, match="Context is not set. Use container_context"):
        DIContainer.context_resource.sync_resolve()
```

## AsyncContextResource
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
    async_resource = providers.AsyncContextResource(create_async_resource)

    
# resolving is the same as for ContextResource
```
