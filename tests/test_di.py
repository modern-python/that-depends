import dataclasses
import logging
import typing

import pytest

from modern_di import providers


logger = logging.getLogger(__name__)


def create_sync_resource() -> typing.Iterator[str]:
    logger.debug("Resource initiated")
    yield "sync resource"
    logger.debug("Resource destructed")


async def create_async_resource() -> typing.AsyncIterator[str]:
    logger.debug("Async resource initiated")
    yield "async resource"
    logger.debug("Async resource destructed")


@dataclasses.dataclass(kw_only=True, slots=True)
class IndependentFactory:
    dep1: str
    dep2: int


@dataclasses.dataclass(kw_only=True, slots=True)
class SyncDependentFactory:
    independent_factory: IndependentFactory
    sync_resource: str


@dataclasses.dataclass(kw_only=True, slots=True)
class AsyncDependentFactory:
    independent_factory: IndependentFactory
    async_resource: str


class DIContainer:
    sync_resource = providers.Resource[str](create_sync_resource)
    async_resource = providers.AsyncResource[str](create_async_resource)

    independent_factory = providers.Factory(IndependentFactory, dep1="text", dep2=123)
    sync_dependent_factory = providers.Factory(
        SyncDependentFactory,
        independent_factory=independent_factory,
        sync_resource=sync_resource,
    )
    async_dependent_factory = providers.Factory(
        AsyncDependentFactory,
        independent_factory=independent_factory,
        async_resource=async_resource,
    )


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
