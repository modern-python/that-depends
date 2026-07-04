---
title: that-depends
---

<div class="mp-hero" markdown>

<h1 class="mp-lockup">
<img class="mp-logo mp-logo--light" src="assets/lockup-light.svg" alt="that-depends">
<img class="mp-logo mp-logo--dark" src="assets/lockup-dark.svg" alt="" aria-hidden="true">
</h1>

</div>

`that-depends` is a python dependency injection framework which, among other things,
supports the following:

- Async and sync dependency resolution
- Scopes and granular context management
- Dependency injection anywhere
- Fully typed and tested
- Compatibility with popular frameworks like `FastAPI` and `LiteStar`
- Python 3.10+ support

---

## Installation

=== "pip"
    ```bash
    pip install that-depends
    ```
=== "uv"
    ```bash
    uv add that-depends
    ```

---

## Quickstart

### Define a creator
```python
async def create_async_resource():
    logger.debug("Async resource initiated")
    try:
        yield "async resource"
    finally:
        logger.debug("Async resource destructed")
```

### Setup Dependency Injection Container with Providers
```python
from that_depends import BaseContainer, providers

class Container(BaseContainer):
    provider = providers.Resource(create_async_resource)
```

See the [containers documentation](introduction/ioc-container.md) for more information on defining the container.

For a list of providers and their usage, see the [providers section](providers/collections.md).
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

See the [injection documentation](introduction/injection.md) for more information.

## Agents

### Skills

`that-depends` ships with an [agent skill in the repository](https://github.com/modern-python/that-depends/tree/main/that_depends/.agents/skills/that-depends).

This can be installed using an appropriate tool, such as [skilly](https://pypi.org/project/skilly/):
```shell
uvx skilly scan
```


### llms.txt

`that-depends` provides a [llms.txt](https://that-depends.modern-python.org/llms.txt) file.

You can find documentation on how to use it [here](https://llmstxt.org/).
