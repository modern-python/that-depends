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
