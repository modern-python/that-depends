import datetime
from dataclasses import dataclass

import pytest

from tests import container
from that_depends import BaseContainer, Provide, inject, providers


async def test_batch_providers_overriding() -> None:
    async_resource_mock = datetime.datetime.fromisoformat("2023-01-01")
    sync_resource_mock = datetime.datetime.fromisoformat("2024-01-01")
    async_factory_mock = datetime.datetime.fromisoformat("2025-01-01")
    simple_factory_mock = container.SimpleFactory(dep1="override", dep2=999)
    singleton_mock = container.SingletonFactory(dep1=False)
    object_mock = object()

    providers_for_overriding = {
        "async_resource": async_resource_mock,
        "sync_resource": sync_resource_mock,
        "simple_factory": simple_factory_mock,
        "singleton": singleton_mock,
        "async_factory": async_factory_mock,
        "object": object_mock,
    }

    with container.DIContainer.override_providers(providers_for_overriding):
        await container.DIContainer.simple_factory()
        dependent_factory = await container.DIContainer.dependent_factory()
        singleton = await container.DIContainer.singleton()
        async_factory = await container.DIContainer.async_factory()
        obj = await container.DIContainer.object()

    assert dependent_factory.simple_factory.dep1 == simple_factory_mock.dep1
    assert dependent_factory.simple_factory.dep2 == simple_factory_mock.dep2
    assert dependent_factory.sync_resource == sync_resource_mock
    assert dependent_factory.async_resource == async_resource_mock
    assert singleton is singleton_mock
    assert async_factory is async_factory_mock
    assert obj is object_mock

    assert (await container.DIContainer.async_resource()) != async_resource_mock


async def test_batch_providers_overriding_sync_resolve() -> None:
    async_resource_mock = datetime.datetime.fromisoformat("2023-01-01")
    sync_resource_mock = datetime.datetime.fromisoformat("2024-01-01")
    simple_factory_mock = container.SimpleFactory(dep1="override", dep2=999)
    singleton_mock = container.SingletonFactory(dep1=False)
    object_mock = object()

    providers_for_overriding = {
        "async_resource": async_resource_mock,
        "sync_resource": sync_resource_mock,
        "simple_factory": simple_factory_mock,
        "singleton": singleton_mock,
        "object": object_mock,
    }

    with container.DIContainer.override_providers(providers_for_overriding):
        container.DIContainer.simple_factory.sync_resolve()
        await container.DIContainer.async_resource.async_resolve()
        dependent_factory = container.DIContainer.dependent_factory.sync_resolve()
        singleton = container.DIContainer.singleton.sync_resolve()
        obj = container.DIContainer.object.sync_resolve()

    assert dependent_factory.simple_factory.dep1 == simple_factory_mock.dep1
    assert dependent_factory.simple_factory.dep2 == simple_factory_mock.dep2
    assert dependent_factory.sync_resource == sync_resource_mock
    assert dependent_factory.async_resource == async_resource_mock
    assert singleton is singleton_mock
    assert obj is object_mock

    assert container.DIContainer.sync_resource.sync_resolve() != sync_resource_mock


def test_providers_overriding_with_context_manager() -> None:
    simple_factory_mock = container.SimpleFactory(dep1="override", dep2=999)

    with container.DIContainer.simple_factory.override_context(simple_factory_mock):
        assert container.DIContainer.simple_factory.sync_resolve() is simple_factory_mock

    assert container.DIContainer.simple_factory.sync_resolve() is not simple_factory_mock


def test_providers_overriding_fail_with_unknown_provider() -> None:
    unknown_provider_name = "unknown_provider_name"
    match = f"Provider with name {unknown_provider_name!r} not found"
    providers_for_overriding = {unknown_provider_name: None}

    with pytest.raises(RuntimeError, match=match), container.DIContainer.override_providers(providers_for_overriding):
        ...  # pragma: no cover


async def test_providers_overriding() -> None:
    async_resource_mock = datetime.datetime.fromisoformat("2023-01-01")
    sync_resource_mock = datetime.datetime.fromisoformat("2024-01-01")
    async_factory_mock = datetime.datetime.fromisoformat("2025-01-01")
    simple_factory_mock = container.SimpleFactory(dep1="override", dep2=999)
    singleton_mock = container.SingletonFactory(dep1=False)
    object_mock = object()
    container.DIContainer.async_resource.override(async_resource_mock)
    container.DIContainer.sync_resource.override(sync_resource_mock)
    container.DIContainer.simple_factory.override(simple_factory_mock)
    container.DIContainer.singleton.override(singleton_mock)
    container.DIContainer.async_factory.override(async_factory_mock)
    container.DIContainer.object.override(object_mock)

    await container.DIContainer.simple_factory()
    dependent_factory = await container.DIContainer.dependent_factory()
    singleton = await container.DIContainer.singleton()
    async_factory = await container.DIContainer.async_factory()
    obj = await container.DIContainer.object()

    assert dependent_factory.simple_factory.dep1 == simple_factory_mock.dep1
    assert dependent_factory.simple_factory.dep2 == simple_factory_mock.dep2
    assert dependent_factory.sync_resource == sync_resource_mock
    assert dependent_factory.async_resource == async_resource_mock
    assert singleton is singleton_mock
    assert async_factory is async_factory_mock
    assert obj is object_mock

    container.DIContainer.reset_override()
    assert (await container.DIContainer.async_resource()) != async_resource_mock


async def test_providers_overriding_sync_resolve() -> None:
    async_resource_mock = datetime.datetime.fromisoformat("2023-01-01")
    sync_resource_mock = datetime.datetime.fromisoformat("2024-01-01")
    simple_factory_mock = container.SimpleFactory(dep1="override", dep2=999)
    singleton_mock = container.SingletonFactory(dep1=False)
    object_mock = object()
    container.DIContainer.async_resource.override(async_resource_mock)
    container.DIContainer.sync_resource.override(sync_resource_mock)
    container.DIContainer.simple_factory.override(simple_factory_mock)
    container.DIContainer.singleton.override(singleton_mock)
    container.DIContainer.object.override(object_mock)

    container.DIContainer.simple_factory.sync_resolve()
    await container.DIContainer.async_resource.async_resolve()
    dependent_factory = container.DIContainer.dependent_factory.sync_resolve()
    singleton = container.DIContainer.singleton.sync_resolve()
    obj = container.DIContainer.object.sync_resolve()

    assert dependent_factory.simple_factory.dep1 == simple_factory_mock.dep1
    assert dependent_factory.simple_factory.dep2 == simple_factory_mock.dep2
    assert dependent_factory.sync_resource == sync_resource_mock
    assert dependent_factory.async_resource == async_resource_mock
    assert singleton is singleton_mock
    assert obj is object_mock

    container.DIContainer.reset_override()
    assert container.DIContainer.sync_resource.sync_resolve() != sync_resource_mock


async def test_provider_tear_down_after_override() -> None:
    default_redis_url = "url_1"
    mock_redis_url = "url_2"

    @dataclass
    class _Settings:
        redis_url: str = default_redis_url

    class _Redis:
        def __init__(self, url: str) -> None:
            self.url = url

    class _DIContainer(BaseContainer):
        settings = providers.Singleton(_Settings)
        redis = providers.Singleton(_Redis, url=settings.redis_url)

    @inject
    def _func(redis: _Redis = Provide[_DIContainer.redis]) -> str:
        return redis.url

    _DIContainer.settings.override(_Settings(redis_url=mock_redis_url))

    assert _func() == mock_redis_url

    _DIContainer.settings.reset_override(tear_down_children=True)
    assert _func() == default_redis_url

    assert _DIContainer.redis.sync_resolve().url == default_redis_url

    _DIContainer.settings.override(_Settings(redis_url=mock_redis_url), tear_down_children=True)

    redis_url = _func()
    assert redis_url == mock_redis_url
