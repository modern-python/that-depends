import logging

import pytest

from that_depends import BaseContainer, providers


logger = logging.getLogger(__name__)


class DIContainer(BaseContainer):
    pass


async def test_init_async_resources() -> None:
    await DIContainer.init_async_resources()


def test_wrong_deprecated_providers_init() -> None:
    with pytest.raises(TypeError, match="Unsupported resource type"):
        providers.AsyncContextResource(lambda: None)  # type: ignore[arg-type,return-value]

    with pytest.raises(TypeError, match="Unsupported resource type"):
        providers.AsyncResource(lambda: None)  # type: ignore[arg-type,return-value]
