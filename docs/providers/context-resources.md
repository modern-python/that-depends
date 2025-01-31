# Context-Dependent Resources

`that_depends` provides a way to manage two types of contexts:

- A *global context* (a dictionary) where you can store objects for later retrieval.
- *Resource-specific contexts*, which are managed by the `ContextResource` provider.

To interact with both types of contexts, there are two separate interfaces:

1. Use the `container_context()` context manager to interact with the global context and manage `ContextResource` providers.
2. Directly manage a `ContextResource` context by using the `SupportsContext` interface, which both containers
   and `ContextResource` providers implement.

---
## Quick Start

You must initialize a context before you can resolve a `ContextResource`.

**Setup:**
```python
import typing

from that_depends import BaseContainer, providers, inject, Provide


async def my_async_resource() -> typing.AsyncIterator[str]:
    print("Initializing async resource")
    try:
        yield "async resource"
    finally:
        print("Teardown of async resource")

def my_sync_resource() -> typing.Iterator[str]:
    print("Initializing sync resource")
    try:
        yield "sync resource"
    finally:
        print("Teardown of sync resource")

class MyContainer(BaseContainer):
    async_resource = providers.ContextResource(my_async_resource)
    sync_resource = providers.ContextResource(my_sync_resource)
```

Then, you can resolve the resource by initializing its context:
```python
@MyContainer.async_resource.context
@inject
async def func(dep: str = Provide[MyContainer.async_resource]):
    return dep

await func()  # returns "async resource"
```
This will initialize a new context for `async_resource` each time `func` is called.

---
## Global Context

A global context can be initialized by using the `container_context` context manager.

```python
from that_depends import container_context, fetch_context_item

async with container_context(global_context={"key": "value"}):
    # run some code
    fetch_context_item("key")  # returns 'value'
```

You can also use `container_context` as a decorator:
```python
@container_context(global_context={"key": "value"})
async def func():
    # run some code
    fetch_context_item("key")
```

The values stored in the `global_context` can be resolved as long as:
1. You are still within the scope of the context manager.
2. You have not initialized a new context:
```python
async with container_context(global_context={"key": "value"}):
    # run some code
    fetch_context_item("key")
    async with container_context():  # this will reset all contexts, including the global context.
        fetch_context_item("key")  # Error! key not found
```

If you want to maintain the global context, you can initialize a new context with the `preserve_global_context` argument:
```python
async with container_context(global_context={"key": "value"}):
    # run some code
    fetch_context_item("key")
    async with container_context(preserve_global_context=True):  # preserves the global context
        fetch_context_item("key")  # returns 'value'
```

Additionally, you can use the `global_context` argument in combination with `preserve_global_context` to
extend the global context. This merges the two contexts together by key, with the new `global_context` taking precedence:
```python
async with container_context(global_context={"key_1": "value_1", "key_2": "value_2"}):
    # run some code
    fetch_context_item("key_1")  # returns 'value_1'
    async with container_context(
        global_context={"key_2": "new_value", "key_3": "value_3"},
        preserve_global_context=True
    ):
        fetch_context_item("key_1")  # returns 'value_1'
        fetch_context_item("key_2")  # returns 'new_value'
        fetch_context_item("key_3")  # returns 'value_3'
```

---

## Context Resources

To resolve a `ContextResource`, you must first initialize a new context for that resource. The simplest way to do this is by entering `container_context()` without passing any arguments:
```python
async with container_context():  # this will make all containers initialize a new context
    await MyContainer.async_resource.async_resolve()  # "async resource"
    MyContainer.sync_resource.sync_resolve()          # "sync resource"
```

Trying to resolve a `ContextResource` without first entering `container_context` will yield a `RuntimeError`:
```python
value = MyContainer.sync_resource.sync_resolve()
 > RuntimeError: Context is not set. Use container_context
```

### Resolving async and sync dependencies

``container_context`` implements both ``AsyncContextManager`` and ``ContextManager``.  
This means you can enter an async context with:

```python
async with container_context():
    ...
```
An async context allows resolution of both sync and async dependencies.

A sync context can be entered using:
```python
with container_context():
    ...
```
A sync context will only allow resolution of sync dependencies:
```python
async def my_func():
    with container_context():  # enter sync context
        # trying to resolve async dependency
        await MyContainer.async_resource.async_resolve()

> RuntimeError: AsyncResource cannot be resolved in a sync context.
```

### More granular context initialization

If you do not wish to simply reinitialize the context for all containers, you can initialize a context for a specific container:
```python
# this will init a new context for all ContextResources in MyContainer and any connected containers.
async with container_context(MyContainer):
    ...
```
Or for a specific resource:
```python
# this will init a new context for the specific resource only.
async with container_context(MyContainer.async_resource):
    ...
```

It is not necessary to use `container_context()` to do this. Instead, you can use the `SupportsContext` interface described 
[here](#quick-reference).

### Context Hierarchy

Resources are cached in the context after their first resolution.  
They are torn down when `container_context` exits:
```python
async with container_context():
    value_outer = await MyContainer.resource.async_resolve()
    async with container_context():
        # new context -> resource will be resolved anew
        value_inner = await MyContainer.resource.async_resolve()
        assert value_inner != value_outer
    # previously resolved value is cached in the outer context
    assert value_outer == await MyContainer.resource.async_resolve()
```

### Resolving resources whenever a function is called

`ContextResource.context()` can also be used as a decorator:
```python
@MyContainer.session.context  # wrap with a session-specific context
@inject
async def insert_into_database(session=Provide[MyContainer.session]):
    ...
```
Each time you call `await insert_into_database()`, a new instance of `session` will be injected.

### Quick reference

| Intention                                             | Using `container_context()`                   | Using `SupportsContext` explicitly         | Using `SupportsContext` decorator |
|-------------------------------------------------------|-----------------------------------------------|--------------------------------------------|-----------------------------------|
| Reset context for all containers in scope             | `async with container_context():`             | Not supported.                             | Not supported.                    |
| Reset only sync contexts for all containers in scope. | `with container_context():`                   | Not supported.                             | Not supported.                    |
| Reset a `provider.ContextResource` context            | `async with container_context(my_provider):`  | `async with my_provider.async_context():`  | `@my_provider.context`            |
| Reset a sync `provider.ContextResource` context       | `with container_context(my_provider):`        | `with my_provider.sync_context():`         | `@my_provider.context`            |
| Reset all resources in a container                   | `async with container_context(my_container):` | `async with my_container.async_context():` | `@my_container.context`           |
| Reset all sync resources in a container              | `with container_context(my_container):`       | `with my_container.sync_context():`        | `@my_container.context`           |

> **Note:** the `context()` wrapper is technically not part of the `SupportsContext` API, however all classes which 
> implement this `SupportsContext` also implement this method. 
---

## Middleware

For `ASGI` applications, `that_depends` provides the `DIContextMiddleware` to manage context resources.

The `DIContextMiddleware` accepts containers and resources as arguments and automatically initializes the context for the provided resources when an endpoint is called.

**Example with `FastAPI`:**
```python
import fastapi
from that_depends.providers import DIContextMiddleware, ContextResource
from that_depends import BaseContainer

MyContainer: BaseContainer
my_context_resource_provider: ContextResource
my_app: fastapi.FastAPI

# This will initialize the context for `my_context_resource_provider` and `MyContainer` whenever an endpoint is called.
my_app.add_middleware(DIContextMiddleware, MyContainer, my_context_resource_provider)

# This will initialize the context for all containers when an endpoint is called.
my_app.add_middleware(DIContextMiddleware)
```

> `DIContextMiddleware` also supports the `global_context` and `preserve_global_context` arguments.
