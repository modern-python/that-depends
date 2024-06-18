# Resource
- Resource initialized only once and have teardown logic.
- Generator function is required.
```python
import typing

from that_depends import BaseContainer, providers


def create_sync_resource() -> typing.Iterator[str]:
    # resource initialization
    yield "sync resource"
    # resource teardown

class DIContainer(BaseContainer):
    sync_resource = providers.Resource(create_sync_resource)
```

# These use cases demonstrate how to use `ContextResource` and `AsyncContextResource` within the `DIContainer`.
## Use Case 1: Synchronous Context Resource

```python
import datetime
import logging
from contextlib import contextmanager
from that_depends.providers.context_resources import ContextResource

logger = logging.getLogger(__name__)

# Define a synchronous context resource creator
def create_sync_context_resource() -> typing.Iterator[datetime.datetime]:
    logger.debug("Resource initiated")
    yield datetime.datetime.now(tz=datetime.timezone.utc)
    logger.debug("Resource destructed")

class DIContainer:
    sync_context_resource = ContextResource(create_sync_context_resource)
```

## Use Case 2: Asynchronous Context Resource

```python
import datetime
import logging
from contextlib import asynccontextmanager
import asyncio
from that_depends.providers.context_resources import AsyncContextResource

logger = logging.getLogger(__name__)

async def create_async_context_resource() -> typing.AsyncIterator[datetime.datetime]:
    logger.debug("Async resource initiated")
    yield datetime.datetime.now(tz=datetime.timezone.utc)
    logger.debug("Async resource destructed")

# Define the DIContainer with the asynchronous context resource
class DIContainer:
    async_context_resource = AsyncContextResource(create_async_context_resource)

async def use_async_context_resource():
    resource = await DIContainer.async_context_resource.async_resolve()
    print(f"Asynchronous resource value: {resource}")

asyncio.run(use_async_context_resource())
```

## Use Case 3: Overriding Context Resources

```python

def create_sync_context_resource() -> typing.Iterator[datetime.datetime]:
    logger.debug("Resource initiated")
    yield datetime.datetime.now(tz=datetime.timezone.utc)
    logger.debug("Resource destructed")

async def create_async_context_resource() -> typing.AsyncIterator[datetime.datetime]:
    logger.debug("Async resource initiated")
    yield datetime.datetime.now(tz=datetime.timezone.utc)
    logger.debug("Async resource destructed")

class DIContainer:
    sync_context_resource = ContextResource(create_sync_context_resource)
    async_context_resource = AsyncContextResource(create_async_context_resource)

def override_sync_context_resource():
    mock_resource = datetime.datetime(1970, 1, 1, tzinfo=datetime.timezone.utc)
    DIContainer.sync_context_resource.override(mock_resource)
    resource = DIContainer.sync_context_resource.sync_resolve()
    print(f"Overridden synchronous resource value: {resource}")
    DIContainer.sync_context_resource.reset_override()

override_sync_context_resource()


async def override_async_context_resource():
    mock_resource = datetime.datetime(1970, 1, 1, tzinfo=datetime.timezone.utc)
    DIContainer.async_context_resource.override(mock_resource)
    resource = await DIContainer.async_context_resource.async_resolve()
    print(f"Overridden asynchronous resource value: {resource}")
    DIContainer.async_context_resource.reset_override()

asyncio.run(override_async_context_resource())
```