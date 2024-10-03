# Singleton

Singleton providers resolve the dependency only once and cache the resolved instance for future injections.

## How it works

```python

import random
from that_depends import providers

def some_function():
    """Generate number between 0.0 and 1.0"""
    return random.random()

# create a Singleton provider
prov = providers.Singleton(some_function)

# provider with call `some_func` and cache the return value
prov.sync_resolve() # 0.3
# provider with return the cached value
prov.sync_resolve() # 0.3
```

## Example with `pydantic-settings`

Lets say we are storing our application configuration using [pydantic-settings](https://docs.pydantic.dev/latest/concepts/pydantic_settings/):

```python
from pydantic_settings import BaseSettings
from that_depends import BaseContainer, providers

class DatabaseConfig(BaseModel):
    address: str = "127.0.0.1"
    port: int = 5432
    db_name: str = "postgres"

class Settings(BaseSettings):
    auth_key: str = "my_auth_key" 
    db: DatabaseConfig = DatabaseConfig()
```

Because we do not want to resolve the configuration each time it is used in our application, we provide it using the `Singleton` provider.

```python
async def get_db_connection(address: str, port:int, db_name: str) -> Connection: 
    ...

class MyContainer(BaseContainer):
    config = providers.Singleton(Settings)
    # provide connection arguments and create a connection provider
    db_connection = providers.AsyncFactory(
        get_db_connection, config.db.address, config.db.port, config.db_name:
    )
```

Now we can inject our database connection where it required using `@inject`:

```python
from that_depends import inject, Provide

@inject
async def with_db_connection(conn: Connection = Provide[MyContainer.db_connection]):
    ...
```

Of course we can also resolve the whole configuration without accessing attributes by running:

```python
# sync resolution
config: Settings = MyContainer.config.sync_resolve()
# async resolution
config: Settings = await MyContainer.config.async_resolve()
# inject the configuration into a function
async def with_config(config: Settings = Provide[MyContainer.config]):
    assert config.auth_key == "my_auth_key"
```
