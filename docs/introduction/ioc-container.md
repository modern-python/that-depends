# IOC-container with dependencies

```python
import dataclasses
import logging
import typing

from that_depends import BaseContainer, providers


logger = logging.getLogger(__name__)


# singleton provider with cleaning up
def create_sync_resource() -> typing.Iterator[str]:
    logger.debug("Resource initiated")
    try:
        yield "sync resource"
    finally:
        logger.debug("Resource destructed")


# same, but async
async def create_async_resource() -> typing.AsyncIterator[str]:
    logger.debug("Async resource initiated")
    try:
        yield "async resource"
    finally:
        logger.debug("Async resource destructed")


@dataclasses.dataclass(kw_only=True, slots=True)
class IndependentFactory:
    dep1: str
    dep2: int


@dataclasses.dataclass(kw_only=True, slots=True)
class DependentFactory:
    independent_factory: IndependentFactory
    sync_resource: str
    async_resource: str


class DIContainer(BaseContainer):
    sync_resource = providers.Resource(create_sync_resource)
    async_resource = providers.Resource(create_async_resource)

    independent_factory = providers.Factory(IndependentFactory, dep1="text", dep2=123)
    dependent_factory = providers.Factory(
        DependentFactory,
        independent_factory=independent_factory,
        sync_resource=sync_resource,
        async_resource=async_resource,
    )

```
