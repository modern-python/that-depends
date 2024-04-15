import typing

from litestar import Controller, Litestar, Router, get
from litestar.di import Provide
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


class DIContainer(BaseContainer):
    bool_fn = providers.Factory(bool_fn, value=False)
    str_fn = providers.Factory(str_fn)
    list_fn = providers.Factory(list_fn)
    int_fn = providers.Factory(int_fn)


class MyController(Controller):
    path = "/controller"
    dependencies = {"controller_dependency": Provide(DIContainer.list_fn)}  # noqa: RUF012

    @get(path="/handler", dependencies={"local_dependency": Provide(DIContainer.int_fn)})
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


my_router = Router(
    path="/router",
    dependencies={"router_dependency": Provide(DIContainer.str_fn)},
    route_handlers=[MyController],
)

# on the app
app = Litestar(route_handlers=[my_router], dependencies={"app_dependency": Provide(DIContainer.bool_fn)}, debug=True)


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
