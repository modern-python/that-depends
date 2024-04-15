import datetime

import pytest

from tests.container import DIContainer
from that_depends import providers


async def test_di() -> None:
    independent_factory = await DIContainer.independent_factory()
    sync_dependent_factory = await DIContainer.sync_dependent_factory()
    async_dependent_factory = await DIContainer.async_dependent_factory()
    sequence = await DIContainer.sequence()
    singleton1 = await DIContainer.singleton()
    singleton2 = await DIContainer.singleton()
    async_factory = await DIContainer.async_factory()

    assert sync_dependent_factory.independent_factory is not independent_factory
    assert sync_dependent_factory.sync_resource == "sync resource"
    assert async_dependent_factory.async_resource == "async resource"
    assert sequence == ["sync resource", "async resource"]
    assert singleton1 is singleton2
    assert isinstance(async_factory, datetime.datetime)


def test_wrong_providers_init() -> None:
    with pytest.raises(RuntimeError, match="Resource must be generator function"):
        providers.Resource[str](lambda: None)  # type: ignore[arg-type,return-value]

    with pytest.raises(RuntimeError, match="AsyncResource must be async generator function"):
        providers.AsyncResource[str](lambda: None)  # type: ignore[arg-type,return-value]


def test_container_init_error() -> None:
    with pytest.raises(RuntimeError, match="DIContainer should not be instantiated"):
        DIContainer()
