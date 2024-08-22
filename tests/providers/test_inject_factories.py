import dataclasses
import typing

import pytest

from tests import container
from that_depends import BaseContainer, providers


@dataclasses.dataclass(kw_only=True, slots=True)
class InjectedFactories:
    sync_factory: typing.Callable[..., container.DependentFactory]
    async_factory: typing.Callable[..., typing.Coroutine[typing.Any, typing.Any, container.DependentFactory]]


class DIContainer(BaseContainer):
    sync_resource = providers.Resource(container.create_sync_resource)
    async_resource = providers.Resource(container.create_async_resource)

    simple_factory = providers.Factory(container.SimpleFactory, dep1="text", dep2=123)
    dependent_factory = providers.Factory(
        container.DependentFactory,
        simple_factory=simple_factory.cast,
        sync_resource=sync_resource.cast,
        async_resource=async_resource.cast,
    )
    injected_factories = providers.Factory(
        InjectedFactories,
        sync_factory=dependent_factory.sync_provider,
        async_factory=dependent_factory.provider,
    )


async def test_async_provider() -> None:
    injected_factories = await DIContainer.injected_factories()
    instance1 = await injected_factories.async_factory()
    instance2 = await injected_factories.async_factory()

    assert isinstance(instance1, container.DependentFactory)
    assert isinstance(instance2, container.DependentFactory)
    assert instance1 is not instance2

    await DIContainer.tear_down()


async def test_sync_provider() -> None:
    injected_factories = await DIContainer.injected_factories()
    with pytest.raises(RuntimeError, match="AsyncResource cannot be resolved synchronously"):
        injected_factories.sync_factory()

    await DIContainer.init_resources()
    instance1 = injected_factories.sync_factory()
    instance2 = injected_factories.sync_factory()

    assert isinstance(instance1, container.DependentFactory)
    assert isinstance(instance2, container.DependentFactory)
    assert instance1 is not instance2

    await DIContainer.tear_down()
