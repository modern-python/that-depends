import datetime as dt

from litestar import Litestar, get
from litestar.di import Provide
from litestar.status_codes import HTTP_200_OK
from litestar.testing import TestClient

from tests import container


@get("/")
async def index(injected: dt.datetime) -> dt.datetime:
    return injected


app = Litestar([index], dependencies={"injected": Provide(container.DIContainer.async_resource)})


async def test_litestar_di() -> None:
    with TestClient(app=app) as client:
        response = client.get("/")
        assert response.status_code == HTTP_200_OK, response.text
        assert (
            dt.datetime.fromisoformat(response.json().replace("Z", "+00:00"))
            == await container.DIContainer.async_resource()
        )
