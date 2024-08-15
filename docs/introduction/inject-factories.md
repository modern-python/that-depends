# Injecting factories

When you need to inject the factory itself, but not the result of its call, use:
1. `.provider` attribute for async resolver
2. `.sync_provider` attribute for sync resolver

Let's first define providers with container:
```python
import dataclasses
import datetime
import typing

from that_depends import BaseContainer, providers


async def create_async_resource() -> typing.AsyncIterator[datetime.datetime]:
    yield datetime.datetime.now(tz=datetime.timezone.utc)


@dataclasses.dataclass(kw_only=True, slots=True)
class SomeFactory:
    start_at: datetime.datetime


@dataclasses.dataclass(kw_only=True, slots=True)
class FactoryWithFactories:
    sync_factory: typing.Callable[..., SomeFactory]
    async_factory: typing.Callable[..., typing.Coroutine[typing.Any, typing.Any, SomeFactory]]


class DIContainer(BaseContainer):
    async_resource = providers.Resource(create_async_resource)
    dependent_factory = providers.Factory(SomeFactory, start_at=async_resource.cast)
    factory_with_factories = providers.Factory(
        FactoryWithFactories,
        sync_factory=dependent_factory.sync_provider,
        async_factory=dependent_factory.provider,
    )
```

Async factory from `.provider` attribute can be used like this:
```python
factory_with_factories = await DIContainer.factory_with_factories()
instance1 = await factory_with_factories.async_factory()
instance2 = await factory_with_factories.async_factory()
assert instance1 is not instance2
```

Sync factory from `.sync_provider` attribute can be used like this:
```python
await DIContainer.init_resources()
factory_with_factories = await DIContainer.factory_with_factories()
instance1 = factory_with_factories.sync_factory()
instance2 = factory_with_factories.sync_factory()
assert instance1 is not instance2
```
