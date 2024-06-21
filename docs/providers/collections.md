# Collections
There are several collection providers: `List` and `Dict`

## List
- List provider contains other providers.
- Resolves into list of dependencies.

```python
import random
from that_depends import BaseContainer, providers


class DIContainer(BaseContainer):
    random_number = providers.Factory(random.random)
    numbers_sequence = providers.List(random_number, random_number)


DIContainer.numbers_sequence.sync_resolve()
# [0.3035656170071561, 0.8280498192037787]
```

## Dict
- Dict provider is a collection of named providers.
- Resolves into dict of dependencies.

```python
import random
from that_depends import BaseContainer, providers


class DIContainer(BaseContainer):
    random_number = providers.Factory(random.random)
    numbers_map = providers.Dict(key1=random_number, key2=random_number)


DIContainer.numbers_map.sync_resolve()
# {'key1': 0.6851384528299208, 'key2': 0.41044920948045294}
```
