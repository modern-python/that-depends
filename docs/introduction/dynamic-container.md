# Dynamic container

You can dynamically assign providers to container:
```python
import datetime

from tests import container
from that_depends import BaseContainer, providers


class DIContainer(BaseContainer):
    sync_resource: providers.Resource[datetime.datetime]
    async_resource: providers.Resource[datetime.datetime]


DIContainer.sync_resource = providers.Resource(container.create_sync_resource)
DIContainer.async_resource = providers.Resource(container.create_async_resource)
```

And than you can use these providers as usual:

```python
sync_resource = await DIContainer.sync_resource()
async_resource = await DIContainer.async_resource()
```
