# Object

Object provider returns an object “as is”.

```python
from that_depends import BaseContainer, providers


class DIContainer(BaseContainer):
    object_provider = providers.Object(1)


assert DIContainer.object_provider() == 1
```
