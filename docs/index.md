# That Depends

Welcome to the `that-depends documentation`!

`that-depends` is a python dependency injection framework which, among other things,
supports the following:
- Async and sync dependency resolution
- Scopes and granular context management
- Dependency injection anywhere
- Compatibility with popular frameworks like `FastAPI` and `LiteStar`

---

## Installation

```bash
pip install that-depends
```

---

## Quickstart

### Describe resources and classes:
```python
async def create_async_resource():
    logger.debug("Async resource initiated")
    try:
        yield "async resource"
    finally:
        logger.debug("Async resource destructed")
```

### Setup Dependency Injection Container
```python
from that_depends import BaseContainer, providers

class Container(BaseContainer):
    provider = providers.Resource(create_async_resource)
```

### Resolve dependencies in your code
```python
await Container.provider()
```

### Inject providers in function arguments
```python
from that_depends import inject, Provide
@inject
async def some_foo(value: str = Provide[Container.provider]):
    return value

await some_foo() # "async resource"
```
