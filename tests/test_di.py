import pytest

from modern_di import providers
from tests.container import DIContainer


@pytest.mark.asyncio()
async def test_di() -> None:
    independent_factory = await DIContainer.independent_factory()
    sync_dependent_factory = await DIContainer.sync_dependent_factory()
    async_dependent_factory = await DIContainer.async_dependent_factory()
    assert sync_dependent_factory.independent_factory is not independent_factory
    assert sync_dependent_factory.sync_resource == "sync resource"
    assert async_dependent_factory.async_resource == "async resource"


def test_wrong_providers_init() -> None:
    with pytest.raises(RuntimeError, match="Resource must be generator function"):
        providers.Resource[str](lambda: None)  # type: ignore[arg-type,return-value]

    with pytest.raises(RuntimeError, match="AsyncResource must be async generator function"):
        providers.AsyncResource[str](lambda: None)  # type: ignore[arg-type,return-value]
