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
- Allows both sync and async creators.
- Can only be resolved asynchronously, even if the creator is sync.
```python
import datetime

from that_depends import BaseContainer, providers


async def async_factory() -> datetime.datetime:
    return datetime.datetime.now(tz=datetime.timezone.utc)


class DIContainer(BaseContainer):
    async_factory = providers.AsyncFactory(async_factory)
```

> Note: If you have a class that has dependencies which need to be resolved asynchronously, you can use `AsyncFactory` to create instances of that class. The factory will handle the async resolution of dependencies.


## Retrieving a provider as a callable

When you use a factory‑based provider such as `Factory` (for sync logic) or `AsyncFactory` (for async logic), the resulting provider instance has two special properties:

- `.provider` returns an *async callable* that, when awaited, resolves the resource.  
- `.provider_sync` returns a *sync callable* that, when called, resolves the resource.

You can think of these as no-argument functions that produce the resource you defined. They behave like calling `resolve()` or `resolve_sync()` directly and are convenient when you want a standalone function handle.

---

### Basic usage

#### Defining providers in a container

Suppose you have a `BaseContainer` subclass that defines both a sync and an async resource:

```python
from that_depends import BaseContainer
from that_depends.providers import Factory, AsyncFactory

def build_sync_message() -> str:
    return "Hello from sync provider!"

async def build_async_message() -> str:
    # Possibly perform async setup, I/O, etc.
    return "Hello from async provider!"

class MyContainer(BaseContainer):
    # Synchronous Factory
    sync_message = Factory(build_sync_message)

    # Asynchronous Factory
    async_message = AsyncFactory(build_async_message)
```

Here, `sync_message` is a `Factory` which calls a plain function, while `async_message` is an `AsyncFactory` which calls an async function.

---

#### Resolving resources via `.provider` and `.provider_sync`

The `.provider` property gives you an *async function* to await, and `.provider_sync` gives you a *synchronous* callable. They effectively wrap `.resolve()` and `.resolve_sync()`.

##### Synchronous resolution

```python
# In a synchronous function or interactive session
>>> msg = MyContainer.sync_message.provider_sync
>>> print(msg())
Hello from sync provider!
```

Here, `provider_sync` is a no-argument function that immediately returns the resolved value.

##### Asynchronous resolution

```python
import asyncio

async def main():
    # Acquire the async resource by awaiting the provider property
    msg = await MyContainer.async_message.provider()
    print(msg)

asyncio.run(main())
```

Within an async function, `MyContainer.async_message.provider` gives a no-argument async function to `await`.

---

### Passing the provider function around

Sometimes you may want to store or pass around the provider function itself (rather than resolving it immediately):

```python
class AnotherClass:
    def __init__(self, sync_factory_callable: callable):
        self._factory_callable = sync_factory_callable

    def get_message(self) -> str:
        return self._factory_callable()


# Passing MyContainer.sync_message.provider_sync to AnotherClass
provider_callable = MyContainer.sync_message.provider_sync
another_instance = AnotherClass(provider_callable)
print(another_instance.get_message())  # "Hello from sync provider!"
```

Because `.provider_sync` is just a callable returning your dependency, it can be shared easily throughout your code.

---

### Example: using factories with parameters

`Factory` and `AsyncFactory` can accept dependencies (including other providers) as parameters:

```python
def greet(name: str) -> str:
    return f"Hello, {name}!"

class MyContainer(BaseContainer):
    name = Factory(lambda: "Alice")
    greeting = Factory(greet, name)
```

```python
>>> greeting_sync_fn = MyContainer.greeting.provider_sync
>>> print(greeting_sync_fn())
Hello, Alice!
```

Under the hood, `greeting` calls `greet` with the result of `name.resolve_sync()`.

---

### Context considerations

If your providers use `ContextResource` or require a named scope (for instance, `REQUEST`), you need to wrap your resolves in a context manager:

```python
import typing

from that_depends import BaseContainer, ContextScopes, container_context
from that_depends.providers import ContextResource, Factory


def create_session() -> typing.Iterator[str]:
    yield "session"


class ContextfulContainer(BaseContainer):
    default_scope = ContextScopes.REQUEST
    session = ContextResource(create_session)
    greeting = Factory(lambda session: f"Hello from {session}", session.cast)


with container_context(ContextfulContainer, scope=ContextScopes.REQUEST):
    result = ContextfulContainer.greeting.provider_sync()
```

Call `.provider_sync` or `.provider` on the factory inside the context, so the resources it depends on are valid within the required scope.
These properties exist only on `Factory` and `AsyncFactory`; resolve a `ContextResource` with `.resolve_sync()` or `.resolve()`.
