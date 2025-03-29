# Singleton Provider

A **Singleton** provider creates its instance once and caches it for all future injections or resolutions. When the instance is first requested (via `resolve_sync()` or `resolve()`), the underlying factory is called. On subsequent calls, the cached instance is returned without calling the factory again.

## How it Works

```python
import random

from that_depends import BaseContainer, Provide, inject, providers


def some_function() -> float:
   """Generate number between 0.0 and 1.0"""
   return random.random()


# define container with `Singleton` provider:
class MyContainer(BaseContainer):
   singleton = providers.Singleton(some_function)


# The provider will call `some_function` once and cache the return value

# 1) Synchronous resolution
MyContainer.singleton.resolve_sync()  # e.g. 0.3
MyContainer.singleton.resolve_sync()  # 0.3 (cached)

# 2) Asynchronous resolution
await MyContainer.singleton.resolve()  # 0.3 (same cached value)


# 3) Injection example
@inject
async def with_singleton(number: float = Provide[MyContainer.singleton]):
   # number == 0.3
   ...
```

### Teardown Support
If you need to reset the singleton (for example, in tests or at application shutdown), you can call:
```python 
await MyContainer.singleton.tear_down()
```
This clears the cached instance, causing a new one to be created the next time `resolve_sync()` or `resolve()` is called.  
*(If you only ever use synchronous resolution, you can call `MyContainer.singleton.tear_down_sync()` instead.)*

For further details refer to the [teardown documentation](../introduction/tear-down.md).

---

## Concurrency Safety

`Singleton` is **thread-safe** and **async-safe**:

1. **Async Concurrency**  
   If multiple coroutines call `resolve()` concurrently, the factory function is guaranteed to be called only once. All callers receive the same cached instance.

2. **Thread Concurrency**  
   If multiple threads call `resolve_sync()` at the same time, the factory is only called once. All threads receive the same cached instance.

```python
import threading
import asyncio


# In async code:
async def main():
   # calling resolve concurrently in different coroutines
   results = await asyncio.gather(
      MyContainer.singleton.resolve(),
      MyContainer.singleton.resolve(),
   )
   # Both results point to the same instance


# In threaded code:
def thread_task():
   instance = MyContainer.singleton.resolve_sync()
   ...


threads = [threading.Thread(target=thread_task) for _ in range(5)]
for t in threads:
   t.start()
```

---

## ThreadLocalSingleton Provider

If you want each *thread* to have its own, separately cached instance, use **ThreadLocalSingleton**. This provider creates a new instance per thread and reuses that instance on subsequent calls *within the same thread*.

```python
import random
import threading
from that_depends.providers import ThreadLocalSingleton


def factory() -> int:
   """Return a random int between 1 and 100."""
   return random.randint(1, 100)


# ThreadLocalSingleton caches an instance per thread
singleton = ThreadLocalSingleton(factory)

# In a single thread:
instance1 = singleton.resolve_sync()  # e.g. 56
instance2 = singleton.resolve_sync()  # 56 (cached in the same thread)


# In multiple threads:
def thread_task():
   return singleton.resolve_sync()


thread1 = threading.Thread(target=thread_task)
thread2 = threading.Thread(target=thread_task)
thread1.start()
thread2.start()

# thread1 and thread2 each get a different cached value
```

You can still use `.resolve()` with `ThreadLocalSingleton`, which will also maintain isolation per thread. However, note that this does *not* isolate instances per asynchronous Task – only per OS thread.

---

## Example with `pydantic-settings`

Consider a scenario where your application configuration is defined via [**pydantic-settings**](https://docs.pydantic.dev/latest/concepts/pydantic_settings/). Often, you only want to parse this configuration (e.g., from environment variables) once, then reuse it throughout the application.

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

### Defining the Container

Below, we define a container with a **Singleton** provider for our settings. We also define a separate async factory that connects to the database using those settings.

```python
from that_depends import BaseContainer, providers

async def get_db_connection(address: str, port: int, db_name: str):
    # e.g., create an async DB connection
    ...

class MyContainer(BaseContainer):
    # We'll parse settings only once
    config = providers.Singleton(Settings)

    # We'll pass the config's DB fields into an async factory for a DB connection
    db_connection = providers.AsyncFactory(
        get_db_connection,
        config.db.address,
        config.db.port,
        config.db.db_name,
    )
```

### Injecting or Resolving in Code

You can now inject these values directly into your functions with the `@inject` decorator:

```python
from that_depends import inject, Provide

@inject
async def with_db_connection(conn = Provide[MyContainer.db_connection]):
    # conn is the created DB connection
    ...
```

Or you can manually resolve them when needed:

```python
# Synchronously resolve the config
cfg = MyContainer.config.resolve_sync()

# Asynchronously resolve the DB connection
connection = await MyContainer.db_connection.resolve()
```

By using `Singleton` for `Settings`, you avoid re-parsing the environment or re-initializing the configuration on each request.
