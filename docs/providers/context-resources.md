# ContextResource

Instances injected with the ``ContextResource`` provider have a managed lifecycle.

```python
async def my_async_resource() -> typing.AsyncIterator[str]
    print("Initializing async resource")
    try:
        yield "async resource"
    finally:
        print("Teardown of async resource")

def my_sync_resource() -> typing.Iterator[str]
    print("Initializing sync resource")
    try:
        yield "sync resource"
    finally:
        print("Teardown of sync resource")

class MyContainer(BaseContainer):
    async_resource = providers.ContextResource(my_async_resource)
    sync_resource = providers.ContextResource(my_sync_resource)
```

To be able to resolve a ``ContextResource`` one must first enter a ``container_context``:
```python
async with container_context():
    await MyContainer.async_resource.async_resolve() # "async resource"
    MyContainer.sync_resource.sync_resolve() # "sync resource"

```

 Trying to resolve a ``ContextResource`` without first entering ``container_context`` will yield an Exception:
```python
value = MyContainer.sync_resource.sync_resolve()
 > RuntimeError: Context is not set. Use container_context
```


### Resolving async and sync dependencies:

``container_context`` implements both ``AsyncContextManager`` and ``ContextManager``. This means that you can enter an async context with:

```python
async with container_context():
    ...
```
An async context will allow resolution of both sync and async dependencies.


A sync context can be entered using:

```python
with container_context():
    ...
```
A sync context will only allow resolution of sync dependencies:
```python
async def my_func():
    with container_context(): # enter sync context
        # try to resolve async depenendency.
        await MyContainer.async_resource.async_resolve()

> RuntimeError: AsyncResource cannot be resolved in an sync context.
```

### Context Heirachy

Each time you enter a ``container_context`` a new context is created in the background. Resouces are cached in the context after first resolution. Resources created in a context are torn down again when ``container_context`` exits.

```python

async with container_context():
    value_outer = await MyContainer.resource.async_resolve()
    async with container_context()
        # new context -> resource will be resolved a new
        value_inner = await MyContainer.resource.async_resolve()
        assert value_inner != value_outer
    # previously resolved value is cached in context.
    assert value_outer == await MyContainer.resource.async_resolve()
```




### Resolving resources whenever a function is called

``container_context`` can be used as a wrapper:

```python

@container_context()
@inject
async def insert_into_database(session = Provide[MyContainer.session]):
    ...
```
Each time ``await insert_into_database()`` is called a new instance of ``session`` will be injected.
