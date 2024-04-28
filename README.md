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
    independent_factory: container.IndependentFactory = Provide[container.DIContainer.independent_factory],
) -> None:
    assert independent_factory.dep1
```

# Quickstart
## Install

```bash
pip install that-depends
```

## Usage
### DI-container with dependencies:
```python
import dataclasses
import logging
import typing

from that_depends import BaseContainer, providers


logger = logging.getLogger(__name__)


def create_sync_resource() -> typing.Iterator[str]:
    logger.debug("Resource initiated")
    yield "sync resource"
    logger.debug("Resource destructed")


async def create_async_resource() -> typing.AsyncIterator[str]:
    logger.debug("Async resource initiated")
    yield "async resource"
    logger.debug("Async resource destructed")


@dataclasses.dataclass(kw_only=True, slots=True)
class IndependentFactory:
    dep1: str
    dep2: int


@dataclasses.dataclass(kw_only=True, slots=True)
class SyncDependentFactory:
    independent_factory: IndependentFactory
    sync_resource: str


@dataclasses.dataclass(kw_only=True, slots=True)
class AsyncDependentFactory:
    independent_factory: IndependentFactory
    async_resource: str


class DIContainer(BaseContainer):
    sync_resource = providers.Resource(create_sync_resource)
    async_resource = providers.AsyncResource(create_async_resource)

    independent_factory = providers.Factory(IndependentFactory, dep1="text", dep2=123)
    sync_dependent_factory = providers.Factory(
        SyncDependentFactory,
        independent_factory=independent_factory,
        sync_resource=sync_resource,
    )
    async_dependent_factory = providers.Factory(
        AsyncDependentFactory,
        independent_factory=independent_factory,
        async_resource=async_resource,
    )

```

### Usage with `Fastapi`:

```python
import contextlib
import typing

import fastapi
from starlette import status
from starlette.testclient import TestClient

from tests import container


@contextlib.asynccontextmanager
async def lifespan_manager(_: fastapi.FastAPI) -> typing.AsyncIterator[None]:
    yield
    await container.DIContainer.tear_down()


app = fastapi.FastAPI(lifespan=lifespan_manager)


@app.get("/")
async def read_root(
        sync_dependency: typing.Annotated[
            container.AsyncDependentFactory,
            fastapi.Depends(container.DIContainer.async_dependent_factory),
        ],
) -> str:
    return sync_dependency.async_resource


client = TestClient(app)

response = client.get("/")
assert response.status_code == status.HTTP_200_OK
assert response.json() == "async resource"

```

### Usage with `Litestar`:
```python
import typing
import fastapi
import contextlib
from litestar import Litestar, get
from litestar.di import Provide
from litestar.status_codes import HTTP_200_OK
from litestar.testing import TestClient

from tests import container


@get("/")
async def index(injected: str) -> str:
    return injected


@contextlib.asynccontextmanager
async def lifespan_manager(_: fastapi.FastAPI) -> typing.AsyncIterator[None]:
    yield
    await container.DIContainer.tear_down()


app = Litestar(
    route_handlers=[index],
    dependencies={"injected": Provide(container.DIContainer.async_resource)},
    lifespan=[lifespan_manager],
)


def test_litestar_di() -> None:
    with (TestClient(app=app) as client):
        response = client.get("/")
        assert response.status_code == HTTP_200_OK, response.text
        assert response.text == "async resource"
```

# Docs
## Providers
### Resource
- Resource initialized only once and have teardown logic.
- Generator function is required.
```python
import typing

from that_depends import BaseContainer, providers


def create_sync_resource() -> typing.Iterator[str]:
    # resource initialization
    yield "sync resource"
    # resource teardown

class DIContainer(BaseContainer):
    sync_resource = providers.Resource(create_sync_resource)
```

### AsyncResource
- Same as `Resource` but async generator function is required.
```python
import typing

from that_depends import BaseContainer, providers


async def create_async_resource() -> typing.AsyncIterator[str]:
    # resource initialization
    yield "async resource"
    # resource teardown


class DIContainer(BaseContainer):
    async_resource = providers.AsyncResource(create_async_resource)
```
### Singleton
- Initialized only once, but without teardown logic.
- Class or simple function is allowed.
```python
import dataclasses

from that_depends import BaseContainer, providers


@dataclasses.dataclass(kw_only=True, slots=True)
class SingletonFactory:
    dep1: bool


class DIContainer(BaseContainer):
    singleton = providers.Singleton(SingletonFactory, dep1=True)
```
### Factory
- Initialized on every call.
- Class or simple function is allowed.
```python
import dataclasses

from that_depends import BaseContainer, providers


@dataclasses.dataclass(kw_only=True, slots=True)
class IndependentFactory:
    dep1: str
    dep2: int


class DIContainer(BaseContainer):
    independent_factory = providers.Factory(IndependentFactory, dep1="text", dep2=123)
```
### AsyncFactory
- Initialized on every call, as `Factory`.
- Async function is required.
```python
import datetime

from that_depends import BaseContainer, providers


async def async_factory() -> datetime.datetime:
    return datetime.datetime.now(tz=datetime.timezone.utc)


class DIContainer(BaseContainer):
    async_factory = providers.Factory(async_factory)
```
### List
- List provider contains other providers.
- Resolves into list of dependencies.

```python
import random
from that_depends import BaseContainer, providers


class DIContainer(BaseContainer):
    random_number = providers.Factory(random.random)
    numbers_sequence = providers.List(random_number, random_number)
```
