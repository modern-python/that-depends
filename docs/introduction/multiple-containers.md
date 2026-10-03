# Usage with multiple containers

You can use providers from other containers as follows:
```python
import datetime
import typing

from that_depends import BaseContainer, providers


def create_sync_resource() -> typing.Iterator[datetime.datetime]:
    yield datetime.datetime.now(tz=datetime.timezone.utc)


async def create_async_resource() -> typing.AsyncIterator[datetime.datetime]:
    yield datetime.datetime.now(tz=datetime.timezone.utc)


class InnerContainer(BaseContainer):
    sync_resource = providers.Resource(create_sync_resource)
    async_resource = providers.Resource(create_async_resource)


class OuterContainer(BaseContainer):
    sequence = providers.List(InnerContainer.sync_resource, InnerContainer.async_resource)
```

But this way you have to manage `InnerContainer` lifecycle:

```python
await InnerContainer.tear_down()
```

Or you can connect sub-containers to the main container:

```python
OuterContainer.connect_containers(InnerContainer)


# this will init resources for `InnerContainer` also
await OuterContainer.init_resources()

# and this will tear down resources for `InnerContainer` also
await OuterContainer.tear_down()
```
