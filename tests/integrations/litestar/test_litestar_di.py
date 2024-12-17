import typing
from functools import partial
from typing import Annotated
from unittest.mock import Mock

from litestar import Controller, Litestar, Router, get
from litestar.di import Provide
from litestar.params import Dependency
from litestar.status_codes import HTTP_200_OK
from litestar.testing import TestClient

from that_depends import BaseContainer, providers


def bool_fn(value: bool) -> bool:
    return value


def str_fn() -> str:
    return ""


def list_fn() -> list[str]:
    return ["some"]


def int_fn() -> int:
    return 1


class SomeService:
    pass


class DIContainer(BaseContainer):
    bool_fn = providers.Factory(bool_fn, value=False)
    str_fn = providers.Factory(str_fn)
    list_fn = providers.Factory(list_fn)
    int_fn = providers.Factory(int_fn)
    some_service = providers.Factory(SomeService)


_NoValidationDependency = partial(Dependency, skip_validation=True)


class MyController(Controller):
    path = "/controller"
    dependencies = {"controller_dependency": Provide(DIContainer.list_fn)}  # noqa: RUF012

    @get(
        path="/handler",
        dependencies={
            "local_dependency": Provide(DIContainer.int_fn),
        },
    )
    async def my_route_handler(
        self,
        app_dependency: bool,
        router_dependency: str,
        controller_dependency: list[str],
        local_dependency: int,
    ) -> dict[str, typing.Any]:
        return {
            "app_dependency": app_dependency,
            "router_dependency": router_dependency,
            "controller_dependency": controller_dependency,
            "local_dependency": local_dependency,
        }

    @get(path="/mock_overriding", dependencies={"some_service": Provide(DIContainer.some_service)})
    async def mock_overriding_endpoint_handler(
        self, some_service: Annotated[SomeService, _NoValidationDependency()]
    ) -> None:
        assert isinstance(some_service, Mock)


my_router = Router(
    path="/router",
    dependencies={"router_dependency": Provide(DIContainer.str_fn)},
    route_handlers=[MyController],
)

# on the app
app = Litestar(route_handlers=[my_router], dependencies={"app_dependency": Provide(DIContainer.bool_fn)}, debug=True)


def test_litestar_endpoint_with_mock_overriding() -> None:
    some_service_mock = Mock()

    with DIContainer.some_service.override_context(some_service_mock), TestClient(app=app) as client:
        response = client.get("/router/controller/mock_overriding")

    assert response.status_code == HTTP_200_OK


def test_litestar_di() -> None:
    with TestClient(app=app) as client:
        response = client.get("/router/controller/handler")
        assert response.status_code == HTTP_200_OK, response.text
        assert response.json() == {
            "app_dependency": False,
            "controller_dependency": ["some"],
            "local_dependency": 1,
            "router_dependency": "",
        }


def test_litestar_di_override_fail_on_provider_override() -> None:
    mock = 12345364758999
    with TestClient(app=app) as client, DIContainer.int_fn.override_context(mock):
        response = client.get("/router/controller/handler")

    assert response.status_code == HTTP_200_OK, response.text
    assert response.json() == {
        "app_dependency": False,
        "controller_dependency": ["some"],
        "local_dependency": mock,
        "router_dependency": "",
    }


def test_litestar_di_override_fail_on_override_providers() -> None:
    mock = 12345364758999
    overrides = {
        "int_fn": mock,
    }
    with TestClient(app=app) as client, DIContainer.override_providers(overrides):
        response = client.get("/router/controller/handler")

    assert response.status_code == HTTP_200_OK, response.text
    assert response.json() == {
        "app_dependency": False,
        "controller_dependency": ["some"],
        "local_dependency": mock,
        "router_dependency": "",
    }
