from that_depends import get_current_scopefrom mypy.nodes import Context

# Named Scopes

Named scopes are a feature that allows one to define the lifecycle of a `ContextResource`. 
In essence, it is a tool to manage when `ContextResources` can be resolved and when they should be finalized.

Before continuing, make sure you are familiar with `ContextResources` providers by reading their [documentation](../providers/context-resources.md).

## Quick start

Per default, `ContextResources` have the named scoep `ANY`, meaning that they can be resolved in any context.
You can change the scope of a `ContextResource` in two ways:

### Setting scope for providers.

1. By setting the `default_scope` attribute in the container class.

    ```python
    class MyContainer(BaseContainer):
        default_scope = ContextScope.APP
        p = providers.ContextResource(my_resource)
    ```

2. By calling the `with_config()` method when creating a `ContextResource`. This will also override the class default.

    ```python
    p = providers.ContextResource(my_resource).with_config(scope=ContextScope.APP)
    ```

### Entering and exiting scopes

Now that you have assigned scopes to providers, you can can enter a named scope using `container_context()`.
After entering a scope you will be able to resolve resources that have been defined with that scope:

```python
from that_depends import container_context

async with container_context(scope=ContextScopes.APP):
    # resolve resources with scope APP
    await my_app_scoped_provider.async_resolve()
```
## Checking the current scope

If you would like to know the current scope you can use the `get_current_scope()` method:

```python
from that_depends.providers.context_resources import get_current_scope, ContextScopes

async with container_context(scope=ContextScopes.APP):
    assert get_current_scope() == ContextScopes.APP
```

## Understanding resolution & strict scope providers

For it to be possible for a `ContextResource` to be resolved, one must first init the context for that resources.
Named scopes basically group `ContextResources` in containers in such a way such that calling `with container_context(scope=ContextScopes.APP)` will 
initialize a new context for all resources that have been defined with the `APP` scope.

Once the context has been initialized, a resource can be resolved, no matter the current scope, for example:

```python
p = providers.ContextResource(my_resource).with_config(scope=ContextScopes.APP)

await p.async_resolve() # will raise an exception

async with container_context(p, scope=None):
    assert get_current_scope() == None
    await p.async_resolve() # will resolve
```

If you would like that resources can only be resolved in the specified scope, you can set the resolution to strict:

```python
p = providers.ContextResource(my_resource).with_config(scope=ContextScopes.APP, strict_scope=True)
async with container_context(p, scope=None):
    await p.async_resolve() # will raise an exception
    
    async with container_context(scope=ContextScopes.APP):
        await p.async_resolve() # will resolve

```

## Predefined scopes

`that-depends` comes with 4 predefined scopes found in the `ContextScopes` class:

- `ANY`: Marker that a resource can be resolved in any scope (even in the `None` scope). This scope cannot be entered, so will not be accepted by any class or method 
   that will involve entering a named scope.


- `APP`: A convenience scope with no special behaviour.


- `REQUEST`: A convenience scope with no special behaviour. 


- `INJECT`: The default scope of the `@inject` wrapper, read more [here](#named-scopes-with-the-inject-wrapper).

> Note that the default scope, before any scope has been entered is the `None` scope, you can pass this scope to providers, but this scope
cannot be entered, thus in all other scenarios passing `None` a `scope` attribute will simply assume you did not specify a scope.

## Named scopes with the `@inject` wrapper

The `@inject` wrapper also supports named scopes. The default scope is `INJECT` but you can pass any scope you like:

```python
@inject(scope=ContextScopes.APP)
def foo(...):
    get_current_scope() # APP
```

If you pass a scope to the `@inject` wrapper, it will enter that named scope before calling the function, and exit the scope after the function has returned. If you don't want any scope to be entered, you can simply pass `None`.

## Implementing custom scopes

If the default scopes do not fit your needs, you can define custom scopes by creating a `ContextScope` object.

```python
from that_depends.providers.context_resources import ContextScope

CUSTOM = ContextScope("CUSTOM")
```

If you want to group all the scopes in one place, simply extend the `ContextScopes` class:

```python
from that_depends.providers.context_resources import ContextScopes, ContextScope

class MyContextScopes(ContextScopes):
    CUSTOM = ContextScope("CUSTOM")
```
