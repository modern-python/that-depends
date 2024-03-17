import typing

import pytest

from tests import container


@pytest.fixture(autouse=True)
async def _clear_di_container() -> typing.AsyncIterator[None]:
    try:
        yield
    finally:
        container.DIContainer.reset_override()
        await container.DIContainer.tear_down()
