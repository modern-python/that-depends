# Usage with `Litestar`

!!! info "See also"
    [`modern-di-litestar`](https://github.com/modern-python/modern-di-litestar) is the equivalent
    Litestar integration for [`modern-di`](https://github.com/modern-python/modern-di), the newer
    sibling DI framework.

```python
import contextlib
import typing

from litestar import Litestar, get
from litestar.di import Provide
from litestar.status_codes import HTTP_200_OK
from litestar.testing import TestClient

from that_depends import BaseContainer, providers


async def create_async_resource() -> typing.AsyncIterator[str]:
    yield "async resource"


class DIContainer(BaseContainer):
    async_resource = providers.Resource(create_async_resource)


@get("/")
async def index(injected: str) -> str:
    return injected


@contextlib.asynccontextmanager
async def lifespan_manager(_: Litestar) -> typing.AsyncIterator[None]:
    try:
        yield
    finally:
        await DIContainer.tear_down()


app = Litestar(
    route_handlers=[index],
    dependencies={"injected": Provide(DIContainer.async_resource)},
    lifespan=[lifespan_manager],
)


def test_litestar_di() -> None:
    with (TestClient(app=app) as client):
        response = client.get("/")
        assert response.status_code == HTTP_200_OK, response.text
        assert response.text == "async resource"
```
