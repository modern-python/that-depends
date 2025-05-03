# Injection into Generator Functions


`that-depends` supports dependency injections into generator functions. However, this comes
with some minor limitations compared to regular functions.


## Quickstart

You can use the `@inject` decorator to inject dependencies into generator functions:

=== "async generator"

    ```python
    @inject
    async def my_generator(value: str = Provide[Container.factory]) -> typing.AsyncGenerator[str, None]:
        yield value
    ```

=== "sync generator"

    ```python
    @inject
    def my_generator(value: str = Provide[Container.factory]) -> typing.Generator[str, None, None]:
        yield value
    ```

=== "async context manager"

    ```python
    @contextlib.asynccontextmanager
    @inject
    async def my_generator(value: str = Provide[Container.factory]) -> typing.AsyncIterator[str]:
        yield value
    ```

=== "sync context manager"

    ```python
    @contextlib.contextmanager
    @inject
    def my_generator(value: str = Provide[Container.factory]) -> typing.Iterator[str]:
        yield value
    ```

## Supported Generators

### Synchronous Generators

`that-depends` supports injection into sync generator functions with the following signature:

```python
Callable[P, Generator[<YieldType>, <SendType>, <ReturnType>]]
```

This means that wrapping a sync generator with `@inject` will always preserve all the behaviour of the wrapped generator:

- It will yield as expected
- It will accept sending values via `send()`
- It will raise `StopIteration` when the generator is exhausted or otherwise returns.


### Asynchronous Generators

`that-depends` supports injection into async generator functions with the following signature:

```python
Callable[P, AsyncGenerator[<YieldType>, None]]
```

This means that wrapping an async generator with `@inject` will have the following effects:

- The generator will yield as expected
- The generator will **not** accept values via `asend()`

If you need to send values to an async generator, you can simply resolve dependencies in the generator body:

```python

async def my_generator() -> typing.AsyncGenerator[float, float]:
    value = await Container.factory.resolve()
    receive = yield value # (1)!
    yield receive + value

```

1. This receive will always be `None` if you would wrap this generator with @inject.



## ContextResources

`that-depends` will **not** allow context initialization for [ContextResource](../providers/context-resources.md) providers 
as part of dependency injection into a generator.

This is the case for both async and sync injection.

**For example:**
```python
def sync_resource() -> typing.Iterator[float]:
    yield random.random() 

class Container(BaseContainer):
    sync_provider = providers.ContextResource(sync_resource).with_config(scope=ContextScopes.INJECT)
    dependent_provider = providers.Factory(lambda x: x, sync_provider.cast)

@inject(scope=ContextScopes.INJECT) # (1)!
def injected(val: float = Provide[Container.dependent_provider]) -> typing.Generator[float, None, None]:
    yield val 

# This will raise a `ContextProviderError`!
next(_injected())
```

1. Matches context scope of `sync_provider` provider, which is a dependency of the `dependent_provider` provider.


When calling `next(injected())`, `that-depends` will try to initialize a new context for the `sync_provider`,
however, this is not permitted for generators, thus it will raise a `ContextProviderError`.


Keep in mind that if context does not need to be initialized, the generator injection will work as expected:

```python
def sync_resource() -> typing.Iterator[float]:
    yield random.random() 

class Container(BaseContainer):
    sync_provider = providers.ContextResource(sync_resource).with_config(scope=ContextScopes.REQUEST)
    dependent_provider = providers.Factory(lambda x: x, sync_provider.cast)

@inject(scope=ContextScopes.INJECT) # (1)!
def injected(val: float = Provide[Container.dependent_provider]) -> typing.Generator[float, None, None]:
    yield val 


with container_context(scope=ContextScopes.REQUEST):
    # This will resolve as expected
    next(_injected())
```

Since no context initialization was needed, the generator will work as expected.

1. Scope provided to `@inject` no longer matches scope of the `sync_provider`
