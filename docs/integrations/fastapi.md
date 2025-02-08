# Usage with `Fastapi`

```python
import contextlib
import typing

import fastapi
from starlette import status
from starlette.testclient import TestClient

from tests import container


@contextlib.asynccontextmanager
async def lifespan_manager(_: fastapi.FastAPI) -> typing.AsyncIterator[None]:
    try:
        yield
    finally:
        await container.DIContainer.tear_down()


app = fastapi.FastAPI(lifespan=lifespan_manager)


@app.get("/")
async def read_root(
    some_dependency: typing.Annotated[
        container.DependentFactory,
        fastapi.Depends(container.DIContainer.dependent_factory),
    ],
) -> str:
    return some_dependency.async_resource


client = TestClient(app)

response = client.get("/")
assert response.status_code == status.HTTP_200_OK
assert response.json() == "async resource"

```
