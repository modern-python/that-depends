# Named Scopes

Named scopes allow you to define the lifecycle of a `ContextResource`. 
In essence, they provide a tool to manage when `ContextResources` can be resolved and when they should be finalized.

Before continuing, make sure you're familiar with `ContextResource` providers by reading their [documentation](../providers/context-resources.md).

## Quick Start

By default, `ContextResources` have the named scope `ANY`, meaning they will be re-initialized each time you enter a named scope.
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
When you call `container_context(scope=ContextScopes.APP)` this both enters the `APP` scope and (re-)initializes context for
all providers that have `APP` scope. Scoped resources will prevent their context initialization if the current scope does
not match their scope:
```python
p = providers.ContextResource(my_resource).with_config(scope=ContextScopes.APP)

async with p.async_context(): 
    # will raise an InvalidContextError since current scope is `None`
    ...
```

Similarly, this will also not work:
```python
async with container_context(p, scope=ContextScopes.REQUEST): 
    # will raise and InvalidContextError since you are entering `REQUEST` scope
    ...
```

Once the context has been initialized, a resource can be resolved regardless of the current scope. For example:

```python
await p.async_resolve()  # will raise an exception

async with container_context(p, scope=ContextScopes.APP):
    val_1 = await p.async_resolve()  # will resolve
    async with container_context(p, scope=ContextScopes.REQUEST):
        val_2 = await p.async_resolve()  # will resolve
        assert val_1 == val_2 # but value stays the same since context is the same
```

If you want resources to be resolved **only** in the specified scope, enable strict resolution:

```python
p = providers.ContextResource(my_resource).with_config(scope=ContextScopes.APP, strict_scope=True)
async with container_context(p, scope=ContextScopes.APP):
    await p.async_resolve() # will resolve
    
    async with container_context(scope=ContextScopes.REQUEST):
        await p.async_resolve()  # will raise an exception
```

## Entering a context by force

If you for some reason need to (re-)initialize a context for a `ContextResource` outside of its defined scope,
you can force enter its context:
```python
p = providers.ContextResource(my_resource).with_config(scope=ContextScopes.APP)

async with p.async_context(force=True):
    assert get_current_scope() == None
    await p.async_resolve() # will resolve
```
Or similarly using the `context` wrapper (both `ContextResource` providers and containers provide this API):
```python
class Container(BaseContainer):
    p = providers.ContextResource(my_resource).with_config(scope=ContextScopes.APP)
    
@Container.context(force=True)
@inject
async def injected(val = Provide[Container.p]):
   return p 

await injected() # will resolve
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

## Named scopes with middleware
You can pass a named scope to the `DIContextMiddleware` to set the scope and pre-initialize scoped `ContextResources` for the entire request:

```python
middleware = DIContextMiddleware(app, scope=ContextScopes.REQUEST)
```
