# Singleton
- Initialized only once, but without teardown logic.
- Class or simple function is allowed.
```python
import dataclasses

from that_depends import BaseContainer, providers


@dataclasses.dataclass(kw_only=True, slots=True)
class SingletonFactory:
    dep1: bool


class DIContainer(BaseContainer):
    singleton = providers.Singleton(SingletonFactory, dep1=True)
```
