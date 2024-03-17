import typing

import fastapi
from starlette import status
from starlette.testclient import TestClient

from tests import container


app = fastapi.FastAPI()


@app.get("/")
async def read_root(
    sync_dependency: typing.Annotated[
        container.AsyncDependentFactory,
        fastapi.Depends(container.DIContainer.async_dependent_factory.resolve),
    ],
) -> str:
    return sync_dependency.async_resource


client = TestClient(app)


def test_read_main() -> None:
    response = client.get("/")
    assert response.status_code == status.HTTP_200_OK
    assert response.json() == "async resource"
