# Injecting providers in `that-depends`

`that-depends` uses a decorator-based approach for both synchronous and asynchronous functions. By decorating a function with `@inject` and marking certain parameters as `Provide[...]`, `that-depends` will automatically resolve the specified providers at call time.

---

## Overview

In `that-depends`, you define your dependencies as `AbstractProvider` instances, such as `Singleton`, `Factory`, or `Resource`. These providers typically live inside a subclass of `BaseContainer`, which makes them globally accessible.

When you want to use a provider in a function, you can mark a parameter's default value as:

```python
my_param = Provide[MyContainer.some_provider]
```

You then decorate the function with `@inject`. This tells `that-depends` to automatically resolve providers when you call your function.

---

## Quick start

This example defines a container, declares a provider, and injects that provider into a function.

### 1. Define a container and a provider

```python
from that_depends import BaseContainer
from that_depends.providers import Singleton

class MyContainer(BaseContainer):
    greeting_provider = Singleton(lambda: "Hello from MyContainer")
```
For more details on containers, refer to the [Containers](ioc-container.md) documentation.

### 2. Inject the provider into a function

```python
from that_depends import inject, Provide

@inject
def greet_user(greeting: str = Provide[MyContainer.greeting_provider]) -> str:
    return f"Greeting: {greeting}"
```

Here:

1. We used `@inject` above `greet_user`.
2. We declared a parameter `greeting`, whose default value is `Provide[MyContainer.greeting_provider]`.

### 3. Call the function

```python
print(greet_user())  # "Greeting: Hello from MyContainer"
```

---

## The `@inject` decorator in detail


### Synchronous and asynchronous functions

`@inject` works on both sync and async functions, but you cannot inject async providers into sync functions.

```python
@inject
async def async_greet_user(greeting: str = Provide[MyContainer.greeting_provider]) -> str:
    # asynchronous operations...
    return f"Greeting: {greeting}"
```

---

## Using `Provide[...]` as a default

Wrap your provider in `Provide[...]` when you use it as a default in an injected function, so that the parameter gets the correct type:

```python
@inject
def greet_user_direct(
        greeting: str = Provide[MyContainer.greeting_provider] # (1)!
    ) -> str: 
    return f"Greeting: {greeting}"
```

1. Notice that although `greeting` is a `str`, `mypy` and your IDE will not complain.

---

## Injection warnings

If `@inject` finds **no** parameters whose default values are providers, it will issue a warning:

> `Expected injection, but nothing found. Remove @inject decorator.`

The warning catches functions decorated by mistake that do not require injection.

---

## Specifying a scope

By default, `@inject` uses the `ContextScopes.INJECT` scope. If you want to override that, do:

```python
from that_depends import inject
from that_depends.providers.context_resources import ContextScopes

@inject(scope=ContextScopes.REQUEST)
def greet_user(greeting: str = Provide[MyContainer.greeting_provider]):
    ...
```

When `greet_user` is called, `that-depends`:

1. Initializes the context for all `REQUEST` (or `ANY`) scoped `args` and `kwargs`.
2. Resolves all providers in the `args` and `kwargs` of the function.
3. Calls your function with the resolved dependencies.

For more details regarding scopes and context management, see the [Context Resources](../providers/context-resources.md) documentation and the [Scopes](scopes.md) documentation.

---

## Overriding providers

In tests or specialized scenarios, you may want to override a provider’s value temporarily. You can do so with the container’s `override_providers_sync()` method or the provider’s own `override_context_sync()`:

```python
def test_greet_override():
    # Override the greeting_provider with a mock value
    with MyContainer.override_providers_sync({"greeting_provider": "TestHello"}):
        result = greet_user()
        assert result == "Greeting: TestHello"
```

This is especially helpful for unit tests where you want to substitute real dependencies (e.g., database connections) with mocks or stubs.

For more details on overriding providers, see the [Overriding Providers](../testing/provider-overriding.md) documentation.

---

## Frequently asked questions

### Do I need to call `@inject` every time I reference a provider?

No, only when you want automatic injection of providers into function parameters. If you resolve dependencies manually (e.g., `MyContainer.greeting_provider.resolve_sync()`), you do not need `@inject`.

### What if I provide a custom argument to a parameter that has a default provider?

A value you pass explicitly overrides the injected default:

~~~~python
@inject
def foo(x: int = Provide[MyContainer.number_factory]) -> int:
    return x

print(foo())     # uses number_factory -> 42
print(foo(99))   # explicitly uses 99
~~~~

### Can I combine `@inject` with other decorators?

Yes. Generally, put `@inject` below the others, depending on the order you need. If you run into issues, experiment with the order or handle context manually.

---
