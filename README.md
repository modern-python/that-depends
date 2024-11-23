"That Depends"
==
[![Test Coverage](https://codecov.io/gh/modern-python/that-depends/branch/main/graph/badge.svg)](https://codecov.io/gh/modern-python/that-depends)
[![MyPy Strict](https://img.shields.io/badge/mypy-strict-blue)](https://mypy.readthedocs.io/en/stable/getting_started.html#strict-mode-and-configuration)
[![Supported versions](https://img.shields.io/pypi/pyversions/that-depends.svg)](https://pypi.python.org/pypi/that-depends)
[![downloads](https://img.shields.io/pypi/dm/that-depends.svg)](https://pypistats.org/packages/that-depends)
[![GitHub stars](https://img.shields.io/github/stars/modern-python/that-depends)](https://github.com/modern-python/that-depends/stargazers)

Dependency injection framework for Python inspired by `dependency-injector`.

It is production-ready and gives you the following:
- Simple async-first DI framework with IOC-container.
- Python 3.10-3.13 support.
- Full coverage by types annotations (mypy in strict mode).
- FastAPI and LiteStar compatibility.
- Overriding dependencies for tests.
- Injecting dependencies in functions and coroutines without wiring.
- Package with zero dependencies.

📚 [Documentation](https://that-depends.readthedocs.io)

# Quickstart
## Install
```bash
pip install that-depends
```

## Describe resources and classes:
```python
import dataclasses
import logging
import typing


logger = logging.getLogger(__name__)


# singleton provider with finalization
def create_sync_resource() -> typing.Iterator[str]:
    logger.debug("Resource initiated")
    try:
        yield "sync resource"
    finally:
        logger.debug("Resource destructed")


# same, but async
async def create_async_resource() -> typing.AsyncIterator[str]:
    logger.debug("Async resource initiated")
    try:
        yield "async resource"
    finally:
        logger.debug("Async resource destructed")


@dataclasses.dataclass(kw_only=True, slots=True)
class DependentFactory:
    sync_resource: str
    async_resource: str
```

## Describe IoC-container
```python
from that_depends import BaseContainer, providers


class DIContainer(BaseContainer):
    sync_resource = providers.Resource(create_sync_resource)
    async_resource = providers.Resource(create_async_resource)

    simple_factory = providers.Factory(SimpleFactory, dep1="text", dep2=123)
    dependent_factory = providers.Factory(
        sync_resource=sync_resource,
        async_resource=async_resource,
    )
```

## Resolve dependencies in your code
```python
# async resolving by default:
await DIContainer.simple_factory()

# sync resolving is also allowed if there is no uninitialized async resources in dependencies
DIContainer.simple_factory.sync_resolve()

# otherwise you can initialize resources beforehand one by one or in one call:
await DIContainer.init_resources()
```

## Resolve dependencies not described in container
```python
@dataclasses.dataclass(kw_only=True, slots=True)
class FreeFactory:
    dependent_factory: DependentFactory
    sync_resource: str

# this way container will try to find providers by names and resolve them to build FreeFactory instance
free_factory_instance = await DIContainer.resolve(FreeFactory)
```

## Inject providers in function arguments
```python
import datetime

from that_depends import inject, Provide

from tests import container


@inject
async def some_coroutine(
    simple_factory: container.SimpleFactory = Provide[container.DIContainer.simple_factory],
    dependent_factory: container.DependentFactory = Provide[container.DIContainer.dependent_factory],
    default_zero: int = 0,
) -> None:
    assert simple_factory.dep1
    assert isinstance(dependent_factory.async_resource, datetime.datetime)
    assert default_zero == 0

@inject
def some_function(
    simple_factory: container.SimpleFactory = Provide[container.DIContainer.simple_factory],
    default_zero: int = 0,
) -> None:
    assert simple_factory.dep1
    assert default_zero == 0
```
