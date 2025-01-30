# Named Scopes

Named scopes allow you to define the lifecycle of a `ContextResource`. 
In essence, they provide a tool to manage when `ContextResources` can be resolved and when they should be finalized.

Before continuing, make sure you're familiar with `ContextResources` providers by reading their [documentation](../providers/context-resources.md).

## Quick Start

By default, `ContextResources` have the named scope `ANY`, meaning they can be resolved in any context.
You can change the scope of a `ContextResource` in two ways:

### Setting the scope for providers

1. By setting the `default_scope` attribute in the container class:

   ```python
   class MyContainer(BaseContainer):
       default_scope = ContextScope.APP
       p = providers.ContextResource(my_resource)
   ```

2. By calling the `with_config()` method when creating a `ContextResource`. This also overrides the class default:

   ```python
   p = providers.ContextResource(my_resource).with_config(scope=ContextScope.APP)
   ```

### Entering and exiting scopes

Once you have assigned scopes to providers, you can enter a named scope using `container_context()`.  
After entering a scope, you can resolve resources that have been defined with that scope:

```python
from that_depends import container_context

async with container_context(scope=ContextScopes.APP):
    # resolve resources with scope APP
    await my_app_scoped_provider.async_resolve()
```

## Checking the current scope

If you want to check the current scope, you can use the `get_current_scope()` function:

```python
from that_depends.providers.context_resources import get_current_scope, ContextScopes

async with container_context(scope=ContextScopes.APP):
    assert get_current_scope() == ContextScopes.APP
```

## Understanding resolution & strict scope providers

In order for a `ContextResource` to be resolved, you must first initialize the context for that resource.  
Named scopes group `ContextResources` in containers such that calling `with container_context(scope=ContextScopes.APP)`  
initializes a new context for all resources defined with the `APP` scope.

Once the context has been initialized, a resource can be resolved regardless of the current scope. For example:

```python
p = providers.ContextResource(my_resource).with_config(scope=ContextScopes.APP)

await p.async_resolve()  # will raise an exception

async with container_context(p, scope=None):
    assert get_current_scope() is None
    await p.async_resolve()  # will resolve
```

If you want resources to be resolved **only** in the specified scope, enable strict resolution:

```python
p = providers.ContextResource(my_resource).with_config(scope=ContextScopes.APP, strict_scope=True)
async with container_context(p, scope=None):
    await p.async_resolve()  # will raise an exception
    
    async with container_context(scope=ContextScopes.APP):
        await p.async_resolve()  # will resolve
```

## Predefined scopes

`that-depends` includes four predefined scopes in the `ContextScopes` class:

- `ANY`: Indicates that a resource can be resolved in any scope (even `None`). This scope cannot be entered, so it won’t be accepted by any class or method that requires entering a named scope.

- `APP`: A convenience scope with no special behavior.

- `REQUEST`: A convenience scope with no special behavior.

- `INJECT`: The default scope of the `@inject` wrapper. Read more in the [Named scopes with the @inject wrapper](#named-scopes-with-the-inject-wrapper) section.

> **Note:** The default scope, before entering any named scope, is `None`. You can pass `None` as a scope to providers, but since it cannot be entered, in most scenarios passing `None` simply means you did not specify a scope.

## Named scopes with the `@inject` wrapper

The `@inject` wrapper also supports named scopes. Its default scope is `INJECT`, but you can pass any scope you like:

```python
@inject(scope=ContextScopes.APP)
def foo(...):
    get_current_scope()  # APP
```

When you pass a scope to the `@inject` wrapper, it enters that scope before calling the function, and exits the scope after the function returns. If you do not want to enter any scope, pass `None`.

## Implementing custom scopes

If the default scopes don’t fit your needs, you can define custom scopes by creating a `ContextScope` object:

```python
from that_depends.providers.context_resources import ContextScope

CUSTOM = ContextScope("CUSTOM")
```

If you want to group all of your scopes in one place, you can extend the `ContextScopes` class:

```python
from that_depends.providers.context_resources import ContextScopes, ContextScope

class MyContextScopes(ContextScopes):
    CUSTOM = ContextScope("CUSTOM")
```
