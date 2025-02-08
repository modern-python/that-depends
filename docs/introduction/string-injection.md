## Provider resolution by name

The `@inject` decorator can be used to inject a provider by its name. This is useful when you want to inject a provider that is not directly imported in the current module.


This serves two primary purposes:

- A higher level of decoupling between container and your code.
- Avoiding circular imports.

---
## Usage

To inject a provider by name, use the `Provide` marker with a string argument that has the following format:

```
Container.Provider[.attribute.attribute...]
```

The string will be validated when it is passed to `Provide[]`, thus will raise an exception
immediately.

**For example**:

```python
from that_depends import BaseContainer, inject, Provide

class Config(BaseSettings):
    name: str = "Damian"

class A(BaseContainer):
    b = providers.Factory(Config)

@inject
def read(val = Provide["A.b.name"]):
    return val

assert read() == "Damian"
```

### Container alias

Containers support aliases:

```python

class A(BaseContainer):
    alias = "C" # replaces the container name.
    b = providers.Factory(Config)

@inject
def read(val = Provide["C.b.name"]): # `A` can no longer be used.
    return val

assert read() == "Damian"
```

---
## Considerations

This feature is primarily intended as a fallback when other options are not optimal or
simply not available, thus is recommended to be used sparingly.

If you do decide to use injection by name, consider the following:

- In order for this type of injection to work, your container must be in scope when the injected function is called:
    ```python
    from that_depends import BaseContainer, inject, Provide
  
    @inject
    def injected(f = Provide["MyContainer.my_provider"]): ...
  
    injected() # will raise an Exception
  
    class MyContainer(BaseContainer):
        my_provider = providers.Factory(some_creator)
  
    injected() # will resolve
    ```
- Validation of whether you have provided a correct container name and provider name will only happen when the function is called.
