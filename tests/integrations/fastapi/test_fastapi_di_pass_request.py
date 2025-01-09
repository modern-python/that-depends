import typing

import fastapi
from starlette import status
from starlette.testclient import TestClient

from tests import container
from that_depends import BaseContainer, container_context, fetch_context_item, providers


async def init_di_context(request: fastapi.Request) -> typing.AsyncIterator[None]:
    async with container_context(global_context={"request": request}):
        yield


app = fastapi.FastAPI(dependencies=[fastapi.Depends(init_di_context)])


class DIContainer(BaseContainer):
    context_request = providers.Factory(
        lambda: fetch_context_item("request"),
    )


@app.get("/")
async def read_root(
    context_request: typing.Annotated[
        container.DependentFactory,
        fastapi.Depends(DIContainer.context_request),
    ],
    request: fastapi.Request,
) -> None:
    assert request is context_request


client = TestClient(app)


async def test_read_main() -> None:
    response = client.get("/")
    assert response.status_code == status.HTTP_200_OK
