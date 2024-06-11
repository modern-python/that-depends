# Selector

- Selector provider chooses between a provider based on a key.
- Resolves into a single dependency.

```python
import os
from typing import Protocol
from that_depends import BaseContainer, providers

class StorageService(Protocol):
    ...

class StorageServiceLocal(StorageService):
    ...

class StorageServiceRemote(StorageService):
    ...

class DIContainer(BaseContainer):
    storage_service = providers.Selector(
        lambda: os.getenv("STORAGE_BACKEND", "local"),
        local=providers.Factory(StorageServiceLocal),
        remote=providers.Factory(StorageServiceRemote),
    )
```
