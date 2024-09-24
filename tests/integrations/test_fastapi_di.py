import datetime
import typing

import fastapi
from starlette import status
from starlette.testclient import TestClient

from tests import container
from that_depends.providers import DIContextMiddleware


app = fastapi.FastAPI()
app.add_middleware(DIContextMiddleware)


@app.get("/")
async def read_root(
    dependency: typing.Annotated[
        container.DependentFactory,
        fastapi.Depends(container.DIContainer.dependent_factory),
    ],
    free_dependency: typing.Annotated[
        container.FreeFactory,
        fastapi.Depends(container.DIContainer.resolver(container.FreeFactory)),
    ],
    singleton: typing.Annotated[
        container.SingletonFactory,
        fastapi.Depends(container.DIContainer.singleton),
    ],
    singleton_attribute: typing.Annotated[bool, fastapi.Depends(container.DIContainer.singleton.dep1)],
) -> datetime.datetime:
    assert dependency.sync_resource == free_dependency.dependent_factory.sync_resource
    assert dependency.async_resource == free_dependency.dependent_factory.async_resource
    assert singleton.dep1 is True
    assert singleton_attribute is True
    return dependency.async_resource


client = TestClient(app)


async def test_read_main() -> None:
    response = client.get("/")
    assert response.status_code == status.HTTP_200_OK
    assert (
        datetime.datetime.fromisoformat(response.json().replace("Z", "+00:00"))
        == await container.DIContainer.async_resource()
    )
