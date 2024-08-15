# ContextResource
- Context resources are resources with scoped lifecycle
- Generator or async generator is required.
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


async def create_async_resource() -> typing.AsyncIterator[str]:
    # resource initialization
    try:
        yield "async resource"
    finally:
        pass  # resource teardown


class DIContainer(BaseContainer):
    context_resource = providers.ContextResource(create_sync_resource)
    async_context_resource = providers.ContextResource(create_async_resource)


async def main() -> None:
    async with container_context():
        # context resource can be resolved only inside of context
        await DIContainer.context_resource.async_resolve()
        await DIContainer.async_context_resource.async_resolve()
    
    # outside the context resolving will fail
    with pytest.raises(RuntimeError, match="Context is not set. Use container_context"):
        DIContainer.context_resource.sync_resolve()
```
