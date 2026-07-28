# Selector

The Selector provider chooses between provider based on a key. This resolves into a single dependency.

The selector can be a callable that returns a string, an instance of `AbstractProvider` or a string.

## Callable selectors

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

## Provider selectors

In this example, we have a Pydantic-Settings class that contains the key to select the provider.

```python
from typing import Literal
from pydantic_settings import BaseSettings

class Settings(BaseSettings):
    storage_backend: Literal["local", "remote"] = "remote"

class DIContainer(BaseContainer):
    settings = providers.Singleton(Settings)
    selector = providers.Selector(
        settings.cast.storage_backend,
        local=providers.Factory(StorageServiceLocal),
        remote=providers.Factory(StorageServiceRemote),
    )
```

## Fixed string selectors

This can be useful for quickly testing.

```python
class DIContainer(BaseContainer):
    selector = providers.Selector(
        "local",
        local=providers.Factory(StorageServiceLocal),
        remote=providers.Factory(StorageServiceRemote),
    )
```
