"That Depends"
==
[![GitHub issues](https://img.shields.io/github/issues/modern-python/that-depends)](https://github.com/modern-python/that-depends/issues)
[![GitHub forks](https://img.shields.io/github/forks/modern-python/that-depends)](https://github.com/modern-python/that-depends/network)
[![GitHub stars](https://img.shields.io/github/stars/modern-python/that-depends)](https://github.com/modern-python/that-depends/stargazers)
[![GitHub license](https://img.shields.io/github/license/modern-python/that-depends)](https://github.com/modern-python/that-depends/blob/main/LICENSE)

This package is dependency injection framework for Python, mostly inspired by `python-dependency-injector`.

It is production-ready and gives you the following:
- Fully-async simple DI framework with IOC-container.
- Python 3.10-3.12 support.
- Full coverage by types annotations (mypy in strict mode).
- FastAPI and Litestar compatibility.
- Zero dependencies.
- Overriding dependencies for tests.

# Main characteristics:
1. Fully async -> means every dependency resolving is async, so you should construct with `await` keyword:
```python
from tests.container import DIContainer

async def main():
    some_dependency = await DIContainer.independent_factory()
```
2. No wiring for injections in function arguments -> achieved by decision that only one instance of container is supported

```python
from tests import container
from that_depends import Provide, inject


@inject
async def some_function(
        independent_factory: container.SimpleFactory = Provide[container.DIContainer.independent_factory],
) -> None:
    assert independent_factory.dep1
```

# Quickstart
## Install

```bash
pip install that-depends
```
