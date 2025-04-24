# Injecting Providers in **that-depends**

`that-depends` uses a decorator-based approach for both synchronous and asynchronous functions. By decorating a function with `@inject` and marking certain parameters as `Provide[...]`, **that-depends** will automatically resolve the specified providers at call time.

---

## Overview

In **that-depends**, you define your dependencies as `AbstractProvider` instances—e.g., `Singleton`, `Factory`, `Resource`, or others. These providers typically live inside a subclass of `BaseContainer`, making them globally accessible.

When you want to use a provider in a function, you can mark a parameter’s **default value** as:

```python
my_param = Provide[MyContainer.some_provider]
```

You then decorate the function with `@inject`. This tells `that-depends` to automatically resolve providers when you call your function.

---

## Quick Start

Below is a simple example demonstrating how to define a container, declare a provider, and inject that provider into a function.

### 1. Define a Container and a Provider

```python
from that_depends import BaseContainer
from that_depends.providers import Singleton

class MyContainer(BaseContainer):
    greeting_provider = Singleton(lambda: "Hello from MyContainer")
```
For more details on Containers, refer to the [Containers](ioc-container.md) documentation.

### 2. Inject the Provider into a Function

```python
from that_depends import inject, Provide

@inject
def greet_user(greeting: str = Provide[MyContainer.greeting_provider]) -> str:
    return f"Greeting: {greeting}"
```

Here:

1. We used `@inject` above `greet_user`.
2. We declared a parameter `greeting`, whose default value is `Provide[MyContainer.greeting_provider]`.

### 3. Call the Function

```python
print(greet_user())  # "Greeting: Hello from MyContainer"
```

---

## The `@inject` Decorator in Detail


### Synchronous vs Asynchronous Functions

`@inject` works on both sync and async functions. Just note that injecting async providers into sync functions is not supported.

```python
@inject
async def async_greet_user(greeting: str = Provide[MyContainer.greeting_provider]) -> str:
    # asynchronous operations...
    return f"Greeting: {greeting}"
```

---

## Using `Provide[...]` as a Default

It is recommended to wrap your provider in `Provide[...]` when using it as a default in an injected function since it provides correct type resolution:

```python
@inject
def greet_user_direct(
        greeting: str = Provide[MyContainer.greeting_provider] # (1)!
    ) -> str: 
    return f"Greeting: {greeting}"
```

1. Notice that although `greeting` is a `str`, `mypy` and you IDE will not complain.

---

## Injection Warnings

If `@inject` finds **no** parameters whose default values are providers, it will issue a warning:

> `Expected injection, but nothing found. Remove @inject decorator.`

This is to avoid accidentally decorating a function that doesn’t actually require injection.

---

## Specifying a Scope

By default, `@inject` enters the scope `ContextScopes.INJECT`. If you want to override that, do:

```python
from that_depends import inject
from that_depends.providers.context_resources import ContextScopes

@inject(scope=ContextScopes.REQUEST)
def greet_user(greeting: str = Provide[MyContainer.greeting_provider]):
    ...
```

When `greet_user` is called, **that-depends**:

1. Initializes the context for all `REQUEST` (or `ANY`) scoped `args` and `kwargs`.
2. Resolves all providers in the `args` and `kwargs` of the function.
3. Calls your function with the resolved dependencies.

For more details regarding scopes and context management, see the [Context Resources](../providers/context-resources.md) documentation and the [Scopes](scopes.md) documentation.

---

## Overriding Providers

In tests or specialized scenarios, you may want to override a provider’s value temporarily. You can do so with the container’s `override_providers()` method or the provider’s own `override_context()`:

```python
def test_greet_override():
    # Override the greeting_provider with a mock value
    with MyContainer.override_providers_sync({"greeting_provider": "TestHello"}):
        result = greet_user()
        assert result == "Greeting: TestHello"
```

This is especially helpful for unit tests where you want to substitute real dependencies (e.g., database connections) with mocks or stubs.

For more details on overring providers, see the [Overriding Providers](../testing/provider-overriding.md) documentation.

---

## Frequently Asked Questions

1. **Do I need to call `@inject` every time I reference a provider?**  
   No—only when you want **automatic** injection of providers into function parameters. If you are resolving dependencies manually (e.g., `MyContainer.greeting_provider.resolve_sync()`), then `@inject` is not needed.

   2. **What if I provide a custom argument to a parameter that has a default provider?**  
      If you explicitly pass a value, that value overrides the injected default:

      ~~~~python
      @inject
      def foo(x: int = Provide[MyContainer.number_factory]) -> int:
          return x

      print(foo())     # uses number_factory -> 42
      print(foo(99))   # explicitly uses 99
      ~~~~

3. **Can I combine `@inject` with other decorators?**  
   Yes, you can. Generally, put `@inject` **below** others, depending on the order you need. If you run into issues, experiment with the order or handle context manually.

---
