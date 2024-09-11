# Factories
Factories are initialized on every call.

## Factory
- Class or simple function is allowed.
```python
import dataclasses

from that_depends import BaseContainer, providers


@dataclasses.dataclass(kw_only=True, slots=True)
class IndependentFactory:
    dep1: str
    dep2: int


class DIContainer(BaseContainer):
    independent_factory = providers.Factory(IndependentFactory, dep1="text", dep2=123)
```

## AsyncFactory
- Async function is required.
```python
import datetime

from that_depends import BaseContainer, providers


async def async_factory() -> datetime.datetime:
    return datetime.datetime.now(tz=datetime.timezone.utc)


class DIContainer(BaseContainer):
    async_factory = providers.AsyncFactory(async_factory)
```
