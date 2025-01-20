# Usage with `Litestar`

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
    try:
        yield
    finally:
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
