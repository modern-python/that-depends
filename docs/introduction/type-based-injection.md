# Type based injection

`that-depends` also supports dependency injection without explicitly referencing
the provider of the dependency.

## Quick Start

In order to make use of this, you need to bind providers to the type they will provide:
```python
class Container(BaseContainer):
    my_provider = providers.Factory(lambda: random.random()).bind(float)
```

Then provide inject into your functions or generators:

=== "Option 1"
    ```python
    @Container.inject
    async def foo(v: float = Provide()):
        return v
    ```
=== "Option 2"
    ```python
    @inject(container=Container)
    async def foo(v: float = Provide()):
        return v
    ```


## Default bind

Per default, providers will **not** be bound to any type, even if your creator 
function has type hints. So make sure to always bind your providers.

You can also bind multiple types to the same provider:
```python
class Container(BaseContainer):
    my_provider = providers.Factory(lambda: random.random()).bind(float, complex)
```

## Contravariant binding

Per default injection will be invariant to the bound types.

If you wish to enable contravariance for your bound types you can do so by setting
`#!python contravariant=True` in the `bind` method:

```python hl_lines="6 9"
class A: ...

class B(A): ...

class Container(BaseContainer):
    my_provider = providers.Factory(lambda: B()).bind(B, contravariant=True)

@Container.inject
async def foo(v: A = Provide()) -> A: # (1)!
    return v
```

1. `v` will receive an instance of `B` since `A` is a supertype of `B`.
