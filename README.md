"That Depends"
==
This package is dependency injection framework for Python, mostly inspired by `python-dependency-injector`.

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
    sync_resource = providers.Resource[str](create_sync_resource)
    async_resource = providers.AsyncResource[str](create_async_resource)

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

# Main decisions:
1. Every dependency resolving is async, so you should construct with `await` keyword:
```python
from tests.container import DIContainer

async def main():
    some_dependency = await DIContainer.independent_factory()
```
2. No containers initialization to avoid wiring -> only one global instance of container is supported
