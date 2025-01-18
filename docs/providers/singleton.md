# Singleton
- resolve the dependency only once and cache the resolved instance for future injections;

## How it works
```python
import random

from that_depends import BaseContainer, Provide, inject, providers


def some_function() -> float:
    """Generate number between 0.0 and 1.0"""
    return random.random()


# define container with `Singleton` provider:
class MyContainer(BaseContainer):
    singleton = providers.Singleton(some_function)


# provider will call `some_func` and cache the return value
MyContainer.singleton.sync_resolve() # 0.3
# provider with return the cached value
MyContainer.singleton.sync_resolve() # 0.3

# async_resolve can be used also
await MyContainer.singleton.async_resolve() # 0.3

# and injection to function arguments can be used also
@inject
async def with_singleton(number: float = Provide[MyContainer.singleton]):
    ...  # number == 0.3
```

## Concurrency safety
`Singleton` is safe to use in threading and asyncio concurrency:
```python
# calling async_resolve concurrently in different coroutines will create only one instance
await MyContainer.singleton.async_resolve()

# calling sync_resolve concurrently in different threads will create only one instance
MyContainer.singleton.sync_resolve()
```
## ThreadLocalSingleton

For cases when you need to have a separate instance for each thread, you can use `ThreadLocalSingleton` provider. It will create a new instance for each thread and cache it for future injections in the same thread.

```python
from that_depends.providers import ThreadLocalSingleton
import threading
import random

# Define a factory function
def factory() -> int:
    return random.randint(1, 100)

# Create a ThreadLocalSingleton instance
singleton = ThreadLocalSingleton(factory)

# Same thread, same instance
instance1 = singleton.sync_resolve() # 56
instance2 = singleton.sync_resolve() # 56

# Example usage in multiple threads
def thread_task():
    instance = singleton.sync_resolve()
    return instance

# Create and start threads
threads = [threading.Thread(target=thread_task) for i in range(2)]
for thread in threads:
    thread.start()
for thread in threads:
    results = thread.join()

# Results will be different for each thread
print(results) # [56, 78]
```


## Example with `pydantic-settings`
Let's say we are storing our application configuration using [pydantic-settings](https://docs.pydantic.dev/latest/concepts/pydantic_settings/):
```python
from pydantic_settings import BaseSettings
from pydantic import BaseModel


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
from that_depends import BaseContainer, providers


async def get_db_connection(address: str, port:int, db_name: str) -> Connection: 
    ...

class MyContainer(BaseContainer):
    config = providers.Singleton(Settings)
    # provide connection arguments and create a connection provider
    db_connection = providers.AsyncFactory(
        get_db_connection, config.db.address, config.db.port, config.db_name
    )
```

Now we can inject our database connection where it's required using `@inject`:

```python
from that_depends import inject, Provide

@inject
async def with_db_connection(conn: Connection = Provide[MyContainer.db_connection]):
    ...
```

Of course, we can also resolve the whole configuration without accessing attributes by running:

```python
# sync resolution
config = MyContainer.config.sync_resolve()
# async resolution
config = await MyContainer.config.async_resolve()
# inject the configuration into a function
async def with_config(config: Settings = Provide[MyContainer.config]):
    assert config.auth_key == "my_auth_key"
```
