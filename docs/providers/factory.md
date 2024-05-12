### Factory
- Initialized on every call.
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
