# Usage with multiple containers

You can use providers from other containers as following:
```python
from tests import container
from that_depends import BaseContainer, providers


class InnerContainer(BaseContainer):
    sync_resource = providers.Resource(container.create_sync_resource)
    async_resource = providers.Resource(container.create_async_resource)


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
