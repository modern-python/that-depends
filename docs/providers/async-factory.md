### AsyncFactory
- Initialized on every call, as `Factory`.
- Async function is required.
```python
import datetime

from that_depends import BaseContainer, providers


async def async_factory() -> datetime.datetime:
    return datetime.datetime.now(tz=datetime.timezone.utc)


class DIContainer(BaseContainer):
    async_factory = providers.Factory(async_factory)
```
