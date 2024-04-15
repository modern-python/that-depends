import dataclasses
import datetime
import logging
import typing

from that_depends import BaseContainer, providers


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


async def async_factory() -> datetime.datetime:
    return datetime.datetime.now(tz=datetime.UTC)


@dataclasses.dataclass(kw_only=True, slots=True)
class SyncDependentFactory:
    independent_factory: IndependentFactory
    sync_resource: str


@dataclasses.dataclass(kw_only=True, slots=True)
class AsyncDependentFactory:
    independent_factory: IndependentFactory
    async_resource: str


@dataclasses.dataclass(kw_only=True, slots=True)
class SingletonFactory:
    dep1: bool


class DIContainer(BaseContainer):
    sync_resource = providers.Resource(create_sync_resource)
    async_resource = providers.AsyncResource(create_async_resource)
    sequence = providers.List(sync_resource, async_resource)

    independent_factory = providers.Factory(IndependentFactory, dep1="text", dep2=123)
    async_factory = providers.AsyncFactory(async_factory)
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
    singleton = providers.Singleton(SingletonFactory, dep1=True)
