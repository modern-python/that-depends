# Tear-down

Certain providers in `that-depends` require explicit finalization. These providers 
implement the `SupportsTeardown` API. Containers also support finalizing their
resources.

## Quick-start

If you are using a provider that supports finalization such as a [Singleton](../providers/singleton.md):

First, define the container & provider.

```python
from that_depends import BaseContainer, providers
import random

class MyContainer(BaseContainer):
    config = providers.Singleton(lambda: random.random())
```

Resolve the provider somewhere in your code

```python
await MyContainer.config()
```

When you want to reset the cached value:

```python
await MyContainer.config.tear_down()
```

For [Resources](../providers/resources.md) this will also call any finalization logic in your 
context manager.

---

## Propagation

Per default `that-depends` will propagate tear-down to dependent providers.

This means that if you have defined a provider `A` that is dependent on provider `B`,
when calling `await B.tear_down()`, this will also execute `await A.tear_down()`.

**For example:**

```python
class MyContainer(BaseContainer):
    B = providers.Singleton(lambda: random.random())
    A = providers.Singleton(lambda x: x, B)

b = await MyContainer.B()
a = await MyContainer.A()

assert a == b

await MyContainer.B.tear_down()
a_new = await MyContainer.A()
assert a_new != a
```

If you do not wish to propagate tear-down simply call `tear_down(propagate=False)` or `tear_down_sync(propagate=False)`.

--- 

## Sync tear-down

If you need to call tear-down from a sync context you can use the `tear_down_sync()` method. However, 
keep in mind that because dependent resources might be async, this will fail to correctly finalize these async
resources.

Per default this will raise a `CannotTearDownSyncError`:

```python
async def async_creator(val: float) -> typing.AsyncIterator[float]:
    yield val
    print("Finalization!")


class MyContainer(BaseContainer):
    B = providers.Singleton(lambda: random.random())
    A = providers.Resource(async_creator, B.cast)


b = await MyContainer.B()
a = await MyContainer.A()

MyContainer.B.tear_down_sync()  # raises
```

If you do not want to see these errors you can reduce this to a `RuntimeWarning`:

```python
MyContainer.B.tear_down_sync(raise_on_async=False)
```

---

## Containers and tear-down

Containers also support the `tear_down` and `tear_down_sync` methods. When calling
`await Container.tear_down()` all providers in the container will be torn down.


`Container.tear_down_sync()` is also implemented but not recommended unless you are sure 
all providers in your container are sync. 

> Container methods do not support the `propagate` & `raise_on_async` arguments, so if you
> need more granular control try to tear down the providers explicitly.
