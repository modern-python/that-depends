import datetime
import typing

import fastapi
import pytest
from starlette import status
from starlette.testclient import TestClient

from tests import container
from that_depends import fetch_context_item
from that_depends.providers import DIContextMiddleware


_GLOBAL_CONTEXT: typing.Final[dict[str, str]] = {"test2": "value2", "test1": "value1"}


@pytest.fixture
def fastapi_app() -> fastapi.FastAPI:
    app = fastapi.FastAPI()
    app.add_middleware(DIContextMiddleware, container.DIContainer, global_context=_GLOBAL_CONTEXT)

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
        context_resource: typing.Annotated[datetime.datetime, fastapi.Depends(container.DIContainer.context_resource)],
    ) -> datetime.datetime:
        assert dependency.sync_resource == free_dependency.dependent_factory.sync_resource
        assert dependency.async_resource == free_dependency.dependent_factory.async_resource
        assert singleton.dep1 is True
        assert singleton_attribute is True
        assert context_resource == await container.DIContainer.context_resource.resolve()
        for key, value in _GLOBAL_CONTEXT.items():
            assert fetch_context_item(key) == value
        return dependency.async_resource

    return app


@pytest.fixture
def fastapi_client(fastapi_app: fastapi.FastAPI) -> TestClient:
    return TestClient(fastapi_app)


async def test_read_main(fastapi_client: TestClient) -> None:
    response = fastapi_client.get("/")
    assert response.status_code == status.HTTP_200_OK
    assert (
        datetime.datetime.fromisoformat(response.json().replace("Z", "+00:00"))
        == await container.DIContainer.async_resource()
    )
