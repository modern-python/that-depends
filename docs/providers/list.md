# List
- List provider contains other providers.
- Resolves into list of dependencies.

```python
import random
from that_depends import BaseContainer, providers


class DIContainer(BaseContainer):
    random_number = providers.Factory(random.random)
    numbers_sequence = providers.List(random_number, random_number)
```
