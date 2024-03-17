import pytest

from tests import container


@pytest.fixture(autouse=True)
async def _clear_di_container() -> None:
    await container.DIContainer.tear_down()
