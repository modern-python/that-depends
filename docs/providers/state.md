# State

The `State` provider stores a value as part of a context.

It is useful when you want to pass a value into your Container that other providers depend on.


## Creating a state provider

The `State` provider does not accept any arguments when it created.
```python
from that_depends import BaseContainer, providers
class Container(BaseContainer):
    my_state: providers.State[int] = providers.State()
```

## Initializing state

=== "async"
    ```python
    
    with Container.my_state.init(42):
        print(await Container.my_state.resolve()) # 42
    
    ```

=== "sync"
    ```python
    with Container.my_state.init(42):
        print(Container.my_state.resolve_sync()) # 42

    ```

> Note: If you try to resolve a `State` provider without initializing it first it will raise an `StateNotInitializedError`.


## Nested state

The `State` provider will always resolve the last initialize value.

```python
with Container.my_state.init(1):
    print(Container.my_state.resolve_sync())  # 1

    with Container.my_state.init(2):
        print(Container.my_state.resolve_sync())  # 2

    print(Container.my_state.resolve_sync())  # 1
```
