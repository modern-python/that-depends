import typing
from unittest.mock import Mock

from litestar import Controller, Litestar, Router, get
from litestar.status_codes import HTTP_200_OK
from litestar.testing import TestClient

from that_depends import BaseContainer, Provide, inject, providers


def bool_fn(value: bool) -> bool:
    return value


def str_fn() -> str:
    return ""


def list_fn() -> list[str]:
    return ["some"]


def int_fn() -> int:
    return 1


class SomeService:
    def func(self) -> str:
        return "original func"


class DIContainer(BaseContainer):
    bool_fn = providers.Factory(bool_fn, value=False)
    str_fn = providers.Factory(str_fn)
    list_fn = providers.Factory(list_fn)
    int_fn = providers.Factory(int_fn)
    some_service = providers.Factory(SomeService)


class MyController(Controller):
    path = "/controller"

    @get(path="/handler")
    @inject
    async def my_route_handler(
        self,
        app_dependency: bool | typing.Any = Provide[DIContainer.bool_fn],  # noqa: ANN401
        router_dependency: str | typing.Any = Provide[DIContainer.str_fn],  # noqa: ANN401
        controller_dependency: list[str] | typing.Any = Provide[DIContainer.list_fn],  # noqa: ANN401
        local_dependency: int | typing.Any = Provide[DIContainer.int_fn],  # noqa: ANN401
        some_service: SomeService | typing.Any = Provide[DIContainer.some_service],  # noqa: ANN401
    ) -> dict[str, typing.Any]:
        return {
            "some_service": some_service.func(),
            "app_dependency": app_dependency,
            "router_dependency": router_dependency,
            "controller_dependency": controller_dependency,
            "local_dependency": local_dependency,
        }

    @get(path="/sync-handler")
    @inject
    def sync_route_handler(
        self,
        app_dependency: bool | typing.Any = Provide[DIContainer.bool_fn],  # noqa: ANN401
        router_dependency: str | typing.Any = Provide[DIContainer.str_fn],  # noqa: ANN401
        controller_dependency: list[str] | typing.Any = Provide[DIContainer.list_fn],  # noqa: ANN401
        local_dependency: int | typing.Any = Provide[DIContainer.int_fn],  # noqa: ANN401
        some_service: SomeService | typing.Any = Provide[DIContainer.some_service],  # noqa: ANN401
    ) -> dict[str, typing.Any]:
        return {
            "some_service": some_service.func(),
            "app_dependency": app_dependency,
            "router_dependency": router_dependency,
            "controller_dependency": controller_dependency,
            "local_dependency": local_dependency,
        }


my_router = Router(
    path="/router",
    route_handlers=[MyController],
)

# on the app
app = Litestar(route_handlers=[my_router], dependencies={}, debug=True)


def test_litestar_di_async() -> None:
    with TestClient(app=app) as client:
        response = client.get("/router/controller/handler")

        assert response.status_code == HTTP_200_OK, response.text
        assert response.json() == {
            "app_dependency": False,
            "controller_dependency": ["some"],
            "local_dependency": 1,
            "router_dependency": "",
            "some_service": "original func",
        }


def test_litestar_di_sync() -> None:
    with TestClient(app=app) as client:
        response = client.get("/router/controller/sync-handler")

        assert response.status_code == HTTP_200_OK, response.text
        assert response.json() == {
            "app_dependency": False,
            "controller_dependency": ["some"],
            "local_dependency": 1,
            "router_dependency": "",
            "some_service": "original func",
        }


def test_litestar_endpoint_with_mock_overriding() -> None:
    some_service_mock = Mock(func=lambda: "mock func")

    with DIContainer.some_service.override_context(some_service_mock), TestClient(app=app) as client:
        response = client.get("/router/controller/handler")

    assert response.json()["some_service"] == "mock func"


def test_litestar_di_override_fail_on_provider_override() -> None:
    with TestClient(app=app) as client, DIContainer.int_fn.override_context(12345364758999):
        response = client.get("/router/controller/handler")

    assert response.status_code == HTTP_200_OK, response.text
    assert response.json() == {
        "app_dependency": False,
        "controller_dependency": ["some"],
        "local_dependency": 12345364758999,
        "router_dependency": "",
        "some_service": "original func",
    }


def test_litestar_di_override_fail_on_override_providers() -> None:
    overrides = {
        "int_fn": 12345364758999,
    }

    with TestClient(app=app) as client, DIContainer.override_providers(overrides):
        response = client.get("/router/controller/handler")

    assert response.status_code == HTTP_200_OK, response.text
    assert response.json() == {
        "app_dependency": False,
        "controller_dependency": ["some"],
        "local_dependency": 12345364758999,
        "router_dependency": "",
        "some_service": "original func",
    }
