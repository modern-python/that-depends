import asyncio
import datetime
import logging
import threading
import time
import typing
import uuid
from contextlib import AsyncExitStack, ExitStack
from unittest.mock import Mock

import pytest

from that_depends import BaseContainer, Provide, fetch_context_item, inject, providers
from that_depends.entities.resource_context import ResourceContext
from that_depends.meta import DefaultScopeNotDefinedError
from that_depends.providers import container_context
from that_depends.providers.context_resources import (
    ContextScope,
    ContextScopes,
    DIContextMiddleware,
    InvalidContextError,
    _enter_named_scope,
    get_current_scope,
)


logger = logging.getLogger(__name__)


def create_sync_context_resource() -> typing.Iterator[str]:
    logger.info("Resource initiated")
    yield f"sync {uuid.uuid4()}"
    logger.info("Resource destructed")


async def create_async_context_resource() -> typing.AsyncIterator[str]:
    logger.info("Async resource initiated")
    yield f"async {uuid.uuid4()}"
    logger.info("Async resource destructed")


class DIContainer(BaseContainer):
    default_scope = ContextScopes.ANY
    sync_context_resource = providers.ContextResource(create_sync_context_resource)
    async_context_resource = providers.ContextResource(create_async_context_resource)
    dynamic_context_resource = providers.Selector(
        lambda: fetch_context_item("resource_type") or "sync",
        sync=sync_context_resource,
        async_=async_context_resource,
    )


class DependentDiContainer(BaseContainer):
    default_scope = ContextScopes.ANY
    dependent_sync_context_resource = providers.ContextResource(create_sync_context_resource)
    dependent_async_context_resource = providers.ContextResource(create_async_context_resource)


DIContainer.connect_containers(DependentDiContainer)


@pytest.fixture(autouse=True)
async def _clear_di_container() -> typing.AsyncIterator[None]:
    try:
        yield
    finally:
        await DIContainer.tear_down()


@pytest.fixture(params=[DIContainer.sync_context_resource, DIContainer.async_context_resource])
def context_resource(request: pytest.FixtureRequest) -> providers.ContextResource[str]:
    return typing.cast(providers.ContextResource[str], request.param)


@pytest.fixture
def sync_context_resource() -> providers.ContextResource[str]:
    return DIContainer.sync_context_resource


@pytest.fixture
def async_context_resource() -> providers.ContextResource[str]:
    return DIContainer.async_context_resource


async def test_context_resource_without_context_init(
    context_resource: providers.ContextResource[str],
) -> None:
    with pytest.raises(RuntimeError, match="Context is not set. Use container_context"):
        await context_resource.async_resolve()

    with pytest.raises(RuntimeError, match="Context is not set. Use container_context"):
        context_resource.sync_resolve()


@container_context()
async def test_context_resource(context_resource: providers.ContextResource[str]) -> None:
    context_resource_result = await context_resource()

    assert await context_resource() is context_resource_result


@container_context()
def test_sync_context_resource(sync_context_resource: providers.ContextResource[str]) -> None:
    context_resource_result = sync_context_resource.sync_resolve()

    assert sync_context_resource.sync_resolve() is context_resource_result


async def test_async_context_resource_in_sync_context(async_context_resource: providers.ContextResource[str]) -> None:
    with pytest.raises(RuntimeError, match="Context is not set. Use container_context"), container_context():
        await async_context_resource()


async def test_context_resource_different_context(
    context_resource: providers.ContextResource[datetime.datetime],
) -> None:
    async with container_context():
        context_resource_instance1 = await context_resource()

    async with container_context():
        context_resource_instance2 = await context_resource()

    assert context_resource_instance1 is not context_resource_instance2


async def test_context_resource_included_context(
    context_resource: providers.ContextResource[datetime.datetime],
) -> None:
    async with container_context():
        context_resource_instance1 = await context_resource()
        async with container_context():
            context_resource_instance2 = await context_resource()

        context_resource_instance3 = await context_resource()

    assert context_resource_instance1 is not context_resource_instance2
    assert context_resource_instance1 is context_resource_instance3


async def test_context_resources_overriding(context_resource: providers.ContextResource[str]) -> None:
    context_resource_mock = datetime.datetime.now(tz=datetime.timezone.utc)
    context_resource.override(context_resource_mock)

    context_resource_result = await context_resource()
    context_resource_result2 = context_resource.sync_resolve()
    assert context_resource_result is context_resource_result2 is context_resource_mock

    DIContainer.reset_override()
    with pytest.raises(RuntimeError, match="Context is not set. Use container_context"):
        await context_resource()


async def test_context_resources_init_and_tear_down() -> None:
    await DIContainer.init_resources()
    await DIContainer.tear_down()


def test_context_resources_wrong_providers_init() -> None:
    with pytest.raises(TypeError, match="Unsupported resource type"):
        providers.ContextResource(lambda: None)  # type: ignore[arg-type,return-value]


async def test_context_resource_with_dynamic_resource() -> None:
    async with container_context(global_context={"resource_type": "sync"}, reset_all_containers=True):
        assert (await DIContainer.dynamic_context_resource()).startswith("sync")

    async with container_context(global_context={"resource_type": "async_"}, reset_all_containers=True):
        assert (await DIContainer.dynamic_context_resource()).startswith("async")

    async with container_context():
        assert (await DIContainer.dynamic_context_resource()).startswith("sync")


async def test_early_exit_of_container_context() -> None:
    with pytest.raises(RuntimeError, match="No context token set for global vars, use __enter__ or __aenter__ first."):
        await container_context().__aexit__(None, None, None)
    with pytest.raises(RuntimeError, match="No context token set for global vars, use __enter__ or __aenter__ first."):
        container_context().__exit__(None, None, None)


async def test_resource_context_early_teardown() -> None:
    context: ResourceContext[str] = ResourceContext(is_async=True)
    assert context.context_stack is None
    context.sync_tear_down()
    assert context.context_stack is None


async def test_teardown_sync_container_context_with_async_resource() -> None:
    resource_context: ResourceContext[typing.Any] = ResourceContext(is_async=True)
    resource_context.context_stack = AsyncExitStack()
    with pytest.raises(RuntimeError, match="Cannot tear down async context in sync mode"):
        resource_context.sync_tear_down()


async def test_sync_container_context_with_different_stack() -> None:
    @container_context()
    @inject
    def some_injected(depth: int, val: str = Provide[DIContainer.sync_context_resource]) -> str:
        if depth > 1:
            return val
        return some_injected(depth + 1)

    some_injected(1)


async def test_async_container_context_with_different_stack() -> None:
    @container_context()
    @inject
    async def some_injected(depth: int, val: str = Provide[DIContainer.async_context_resource]) -> str:
        if depth > 1:
            return val
        return await some_injected(depth + 1)

    await some_injected(1)


async def test_async_injection_when_resetting_resource_specific_context(
    async_context_resource: providers.ContextResource[str],
) -> None:
    """Async context resources should be able to reset the context for themselves."""

    @async_context_resource.context
    @inject
    async def _async_injected(val: str = Provide[async_context_resource]) -> str:
        assert isinstance(async_context_resource._fetch_context().context_stack, AsyncExitStack)
        return val

    async_result = await _async_injected()
    assert async_result != await _async_injected()
    assert isinstance(async_result, str)


async def test_sync_injection_when_resetting_resource_specific_context(
    sync_context_resource: providers.ContextResource[str],
) -> None:
    """Sync context resources should be able to reset the context for themselves."""

    @sync_context_resource.context
    @inject
    async def _async_injected(val: str = Provide[sync_context_resource]) -> str:
        assert isinstance(sync_context_resource._fetch_context().context_stack, ExitStack)
        return val

    @sync_context_resource.context
    @inject
    def _sync_injected(val: str = Provide[sync_context_resource]) -> str:
        assert isinstance(sync_context_resource._fetch_context().context_stack, ExitStack)
        return val

    async_result = await _async_injected()
    assert async_result != await _async_injected()
    assert isinstance(async_result, str)
    sync_result = _sync_injected()
    assert sync_result != _sync_injected()
    assert isinstance(sync_result, str)


@pytest.mark.repeat(10)
async def test_async_context_resource_asyncio_concurrency() -> None:
    calls: int = 0

    async def create_client() -> typing.AsyncIterator[str]:
        nonlocal calls
        calls += 1
        await asyncio.sleep(0)
        yield ""

    resource = providers.ContextResource(create_client)

    async def resolve_resource() -> str:
        return await resource.async_resolve()

    async with resource.async_context():
        await asyncio.gather(resolve_resource(), resolve_resource())

    assert calls == 1


@pytest.mark.repeat(10)
async def test_sync_context_resource_asyncio_concurrency() -> None:
    calls: int = 0

    def create_client() -> typing.Iterator[str]:
        nonlocal calls
        calls += 1
        yield ""

    resource = providers.ContextResource(create_client)

    async def resolve_resource() -> str:
        return resource.sync_resolve()

    with resource.sync_context():
        await asyncio.gather(resolve_resource(), resolve_resource())

    assert calls == 1


async def test_async_injection_when_explicitly_resetting_resource_specific_context(
    async_context_resource: providers.ContextResource[str],
) -> None:
    """Async context resources should be able to reset the context for themselves explicitly."""

    @async_context_resource.async_context()
    @inject
    async def _async_injected(val: str = Provide[async_context_resource]) -> str:
        assert isinstance(async_context_resource._fetch_context().context_stack, AsyncExitStack)
        return val

    async_result = await _async_injected()
    assert async_result != await _async_injected()
    assert isinstance(async_result, str)


async def test_sync_injection_when_explicitly_resetting_resource_specific_context(
    sync_context_resource: providers.ContextResource[str],
) -> None:
    """Sync context resources should be able to reset the context for themselves explicitly."""

    @sync_context_resource.async_context()
    @inject
    async def _async_injected(val: str = Provide[sync_context_resource]) -> str:
        assert isinstance(sync_context_resource._fetch_context().context_stack, ExitStack)
        return val

    @sync_context_resource.sync_context()
    @inject
    def _sync_injected(val: str = Provide[sync_context_resource]) -> str:
        assert isinstance(sync_context_resource._fetch_context().context_stack, ExitStack)
        return val

    async_result = await _async_injected()
    assert async_result != await _async_injected()
    assert isinstance(async_result, str)
    sync_result = _sync_injected()
    assert sync_result != _sync_injected()
    assert isinstance(sync_result, str)


async def test_async_resolution_when_explicitly_resolving(
    async_context_resource: providers.ContextResource[str],
) -> None:
    """Async context should cache resources until a new one is created."""
    async with async_context_resource.async_context():
        val_1 = await async_context_resource.async_resolve()
        val_2 = await async_context_resource.async_resolve()
        assert val_1 == val_2
        async with async_context_resource.async_context():
            val_3 = await async_context_resource.async_resolve()
            assert val_1 != val_3
            async with async_context_resource.async_context():
                val_4 = await async_context_resource.async_resolve()
                assert val_1 != val_4 != val_3
            val_5 = await async_context_resource.async_resolve()
            assert val_5 == val_3
        val_6 = await async_context_resource.async_resolve()
        assert val_6 == val_1


def test_sync_resolution_when_explicitly_resolving(
    sync_context_resource: providers.ContextResource[str],
) -> None:
    """Sync context should cache resources until a new one is created."""
    with sync_context_resource.sync_context():
        val_1 = sync_context_resource.sync_resolve()
        val_2 = sync_context_resource.sync_resolve()
        assert val_1 == val_2
        with sync_context_resource.sync_context():
            val_3 = sync_context_resource.sync_resolve()
            assert val_1 != val_3
            with sync_context_resource.sync_context():
                val_4 = sync_context_resource.sync_resolve()
                assert val_1 != val_4 != val_3
            val_5 = sync_context_resource.sync_resolve()
            assert val_5 == val_3
        val_6 = sync_context_resource.sync_resolve()
        assert val_6 == val_1


def test_sync_container_context_resolution(
    sync_context_resource: providers.ContextResource[str],
) -> None:
    """container_context should reset context for sync provider."""
    with container_context(sync_context_resource):
        val_1 = sync_context_resource.sync_resolve()
        val_2 = sync_context_resource.sync_resolve()
        assert val_1 == val_2
        with container_context(sync_context_resource):
            val_3 = sync_context_resource.sync_resolve()
            assert val_3 != val_1
        val_4 = sync_context_resource.sync_resolve()
        assert val_4 == val_1
    with pytest.raises(RuntimeError):
        sync_context_resource.sync_resolve()


async def test_async_container_context_resolution(
    async_context_resource: providers.ContextResource[str],
) -> None:
    """container_context should reset context for async provider."""
    async with container_context(async_context_resource):
        val_1 = await async_context_resource.async_resolve()
        val_2 = await async_context_resource.async_resolve()
        assert val_1 == val_2
        async with container_context(async_context_resource):
            val_3 = await async_context_resource.async_resolve()
            assert val_3 != val_1
        val_4 = await async_context_resource.async_resolve()
        assert val_4 == val_1
    with pytest.raises(RuntimeError):
        await async_context_resource.async_resolve()


async def test_async_global_context_resolution() -> None:
    with pytest.raises(RuntimeError):
        async with AsyncExitStack() as stack:
            await stack.enter_async_context(container_context(preserve_global_context=True))
    my_global_resources = {"test_1": "test_1", "test_2": "test_2"}

    async with container_context(global_context=my_global_resources):
        for key, item in my_global_resources.items():
            assert fetch_context_item(key) == item

        async with container_context(preserve_global_context=True):
            for key, item in my_global_resources.items():
                assert fetch_context_item(key) == item

            async with container_context(preserve_global_context=False):
                for key in my_global_resources:
                    assert fetch_context_item(key) is None

            for key, item in my_global_resources.items():
                assert fetch_context_item(key) == item

        for key, item in my_global_resources.items():
            assert fetch_context_item(key) == item
    with pytest.raises(RuntimeError):
        fetch_context_item("test_1")


def test_sync_global_context_resolution() -> None:
    with pytest.raises(RuntimeError), ExitStack() as stack:
        stack.enter_context(container_context(preserve_global_context=True))
    my_global_resources = {"test_1": "test_1", "test_2": "test_2"}
    with container_context(global_context=my_global_resources):
        for key, item in my_global_resources.items():
            assert fetch_context_item(key) == item
        with container_context(preserve_global_context=True):
            for key, item in my_global_resources.items():
                assert fetch_context_item(key) == item
            with container_context(preserve_global_context=False):
                for key in my_global_resources:
                    assert fetch_context_item(key) is None
            for key, item in my_global_resources.items():
                assert fetch_context_item(key) == item
        for key, item in my_global_resources.items():
            assert fetch_context_item(key) == item

    with pytest.raises(RuntimeError):
        fetch_context_item("test_1")


async def test_async_global_context_reset(async_context_resource: providers.ContextResource[str]) -> None:
    """container_context should reset async providers."""
    async with container_context():
        val_1 = await async_context_resource.async_resolve()
        val_2 = await async_context_resource.async_resolve()
        assert val_1 == val_2
        async with container_context():
            val_3 = await async_context_resource.async_resolve()
            assert val_3 != val_1
        val_4 = await async_context_resource.async_resolve()
        assert val_4 == val_1


def test_sync_global_context_reset(sync_context_resource: providers.ContextResource[str]) -> None:
    """container_context should reset sync providers."""
    with container_context():
        val_1 = sync_context_resource.sync_resolve()
        val_2 = sync_context_resource.sync_resolve()
        assert val_1 == val_2
        with container_context():
            val_3 = sync_context_resource.sync_resolve()
            assert val_3 != val_1
        val_4 = sync_context_resource.sync_resolve()
        assert val_4 == val_1


async def test_async_context_with_container(
    async_context_resource: providers.ContextResource[str],
    sync_context_resource: providers.ContextResource[str],
) -> None:
    """Containers should enter async context for all its providers."""
    async with DIContainer.async_context():
        val_1 = await async_context_resource.async_resolve()
        val_2 = await async_context_resource.async_resolve()
        assert val_1 == val_2
        val_1_sync = sync_context_resource.sync_resolve()
        val_2_sync = sync_context_resource.sync_resolve()
        assert val_1_sync == val_2_sync
        async with DIContainer.async_context():
            val_3 = await async_context_resource.async_resolve()
            val_3_sync = sync_context_resource.sync_resolve()
            assert val_3 != val_1
            assert val_3_sync != val_1_sync
        val_4 = await async_context_resource.async_resolve()
        val_4_sync = sync_context_resource.sync_resolve()
        assert val_4 == val_1
        assert val_4_sync == val_1_sync


def test_sync_context_with_container(
    sync_context_resource: providers.ContextResource[str],
) -> None:
    """Containers should enter sync context for all its providers."""
    with DIContainer.sync_context():
        val_1 = sync_context_resource.sync_resolve()
        val_2 = sync_context_resource.sync_resolve()
        assert val_1 == val_2
        with DIContainer.sync_context():
            val_3 = sync_context_resource.sync_resolve()
            assert val_3 != val_1
        val_4 = sync_context_resource.sync_resolve()
        assert val_4 == val_1


async def test_async_container_context_wrapper(async_context_resource: providers.ContextResource[str]) -> None:
    """Container context wrapper should correctly enter async context for wrapped function."""

    @DIContainer.context
    @inject
    async def _injected(val: str = Provide[async_context_resource]) -> str:
        return val

    assert await _injected() != await _injected()

    @DIContainer.async_context()
    @inject
    async def _explicit_injected(val: str = Provide[async_context_resource]) -> str:
        return val

    assert await _explicit_injected() != await _explicit_injected()


def test_sync_container_context_wrapper(sync_context_resource: providers.ContextResource[str]) -> None:
    """Container context wrapper should correctly enter sync context for wrapped function."""

    @DIContainer.context
    @inject
    def _injected(val: str = Provide[sync_context_resource]) -> str:
        return val

    assert _injected() != _injected()

    @DIContainer.sync_context()
    @inject
    def _explicit_injected(val: str = Provide[sync_context_resource]) -> str:
        return val

    assert _explicit_injected() != _explicit_injected()


async def test_async_context_resource_with_dependent_container() -> None:
    """Container should initialize async context resource for dependent containers."""
    async with DIContainer.async_context():
        val_1 = await DependentDiContainer.dependent_async_context_resource.async_resolve()
        val_2 = await DependentDiContainer.dependent_async_context_resource.async_resolve()
        assert val_1 == val_2


def test_sync_context_resource_with_dependent_container() -> None:
    """Container should initialize sync context resource for dependent containers."""
    with DIContainer.sync_context():
        val_1 = DependentDiContainer.dependent_sync_context_resource.sync_resolve()
        val_2 = DependentDiContainer.dependent_sync_context_resource.sync_resolve()
        assert val_1 == val_2


def test_containers_support_sync_context() -> None:
    assert DIContainer.supports_sync_context()


def test_enter_sync_context_for_async_resource_should_throw(
    async_context_resource: providers.ContextResource[str],
) -> None:
    with pytest.raises(RuntimeError):
        async_context_resource._enter_sync_context()


def test_exit_sync_context_before_enter_should_throw(sync_context_resource: providers.ContextResource[str]) -> None:
    with pytest.raises(RuntimeError):
        sync_context_resource._exit_sync_context()


async def test_exit_async_context_before_enter_should_throw(
    async_context_resource: providers.ContextResource[str],
) -> None:
    with pytest.raises(RuntimeError):
        await async_context_resource._exit_async_context()


def test_enter_sync_context_from_async_resource_should_throw(
    async_context_resource: providers.ContextResource[str],
) -> None:
    with pytest.raises(RuntimeError), ExitStack() as stack:
        stack.enter_context(async_context_resource.sync_context())


async def test_preserve_globals_and_initial_context() -> None:
    initial_context = {"test_1": "test_1", "test_2": "test_2"}

    async with container_context(global_context=initial_context):
        for key, item in initial_context.items():
            assert fetch_context_item(key) == item
        new_context = {"test_3": "test_3"}
        async with container_context(global_context=new_context, preserve_global_context=True):
            for key, item in new_context.items():
                assert fetch_context_item(key) == item
            for key, item in initial_context.items():
                assert fetch_context_item(key) == item
        for key, item in initial_context.items():
            assert fetch_context_item(key) == item
        for key in new_context:
            assert fetch_context_item(key) is None


async def test_async_context_switching_with_asyncio() -> None:
    async def slow_async_creator() -> typing.AsyncIterator[str]:
        await asyncio.sleep(0.1)
        yield str(uuid.uuid4())

    class MyContainer(BaseContainer):
        default_scope = None
        slow_provider = providers.ContextResource(slow_async_creator)

    async def _injected() -> str:
        async with MyContainer.slow_provider.async_context():
            return await MyContainer.slow_provider.async_resolve()

    await asyncio.gather(*[_injected() for _ in range(10)])


def test_sync_context_switching_with_threads() -> None:
    def slow_sync_creator() -> typing.Iterator[str]:
        time.sleep(0.1)
        yield str(uuid.uuid4())

    class MyContainer(BaseContainer):
        default_scope = None
        slow_provider = providers.ContextResource(slow_sync_creator)

    def _injected() -> str:
        with MyContainer.slow_provider.sync_context():
            return MyContainer.slow_provider.sync_resolve()

    threads = [threading.Thread(target=_injected) for _ in range(10)]

    for thread in threads:
        thread.start()

    for thread in threads:
        thread.join()


def test_default_named_scope_is_none() -> None:
    assert get_current_scope() is None


def test_entering_scope_sets_current_scope() -> None:
    with _enter_named_scope(ContextScopes.INJECT):
        assert get_current_scope() == ContextScopes.INJECT
    assert get_current_scope() is None


def test_entering_scope_with_container_context_sync() -> None:
    with container_context(scope=ContextScopes.INJECT):
        assert get_current_scope() == ContextScopes.INJECT
    assert get_current_scope() is None


async def test_entering_scope_with_container_context_async() -> None:
    async with container_context(scope=ContextScopes.INJECT):
        assert get_current_scope() == ContextScopes.INJECT
    assert get_current_scope() is None


def test_scoped_provider_get_scope() -> None:
    provider = providers.ContextResource(create_async_context_resource)
    assert provider.get_scope() == ContextScopes.ANY
    provider = provider.with_config(scope=ContextScopes.INJECT)
    assert provider.get_scope() == ContextScopes.INJECT


def test_scoped_container_get_scope() -> None:
    class _Container(BaseContainer): ...

    assert _Container.get_scope() is ContextScopes.ANY

    class _ScopedContainer(BaseContainer):
        default_scope = ContextScopes.INJECT

    assert _ScopedContainer.get_scope() == ContextScopes.INJECT


def test_sync_resolve_scoped_resource() -> None:
    provider = providers.ContextResource(create_sync_context_resource).with_config(scope=ContextScopes.INJECT)
    with pytest.raises(RuntimeError):
        provider.sync_resolve()

    with container_context(provider, scope=ContextScopes.INJECT):
        assert provider.sync_resolve() is not None


async def test_async_resolve_scoped_resource() -> None:
    provider = providers.ContextResource(create_async_context_resource).with_config(scope=ContextScopes.INJECT)
    with pytest.raises(RuntimeError):
        await provider.async_resolve()

    async with container_context(provider, scope=ContextScopes.INJECT):
        assert await provider.async_resolve() is not None


async def test_async_resolve_non_scoped_in_named_context() -> None:
    provider = providers.ContextResource(create_async_context_resource)
    async with container_context(provider, scope=ContextScopes.INJECT):
        assert await provider.async_resolve() is not None


def test_sync_resolve_non_scoped_in_named_context() -> None:
    provider = providers.ContextResource(create_sync_context_resource)
    with container_context(provider, scope=ContextScopes.INJECT):
        assert provider.sync_resolve() is not None


async def test_async_container_init_context_for_scoped_resources() -> None:
    class _Container(BaseContainer):
        async_resource = providers.ContextResource(create_async_context_resource).with_config(
            scope=ContextScopes.INJECT
        )

    async with container_context(scope=ContextScopes.INJECT):
        assert await _Container.async_resource.async_resolve() is not None
    with pytest.raises(RuntimeError):
        async with container_context(scope=None):
            assert await _Container.async_resource.async_resolve() is not None


def test_sync_container_init_context_for_scoped_resources() -> None:
    class _Container(BaseContainer):
        sync_resource = providers.ContextResource(create_sync_context_resource).with_config(scope=ContextScopes.INJECT)

    with container_context(scope=ContextScopes.INJECT):
        assert _Container.sync_resource.sync_resolve() is not None
    with pytest.raises(RuntimeError), container_context(scope=None):
        assert _Container.sync_resource.sync_resolve() is not None


async def test_sync_container_init_context_for_default_container_resources() -> None:
    class _Container(BaseContainer):
        default_scope = ContextScopes.INJECT
        sync_resource = providers.ContextResource(create_sync_context_resource)

    assert _Container.sync_resource.get_scope() == ContextScopes.INJECT
    with container_context(scope=ContextScopes.INJECT):
        assert _Container.sync_resource.sync_resolve() is not None


def test_container_with_context_resources_must_have_default_scope_set() -> None:
    with pytest.raises(DefaultScopeNotDefinedError):

        class _Container(BaseContainer):
            sync_resource = providers.ContextResource(create_sync_context_resource)


def test_providers_with_explicit_scope_ignore_default_scope() -> None:
    class _Container(BaseContainer):
        default_scope = None
        sync_resource = providers.ContextResource(create_sync_context_resource).with_config(scope=ContextScopes.INJECT)

    assert _Container.sync_resource.get_scope() == ContextScopes.INJECT


async def test_none_scoped_provider_should_not_be_resolvable_in_named_scope_async() -> None:
    provider = providers.ContextResource(create_async_context_resource).with_config(scope=None)
    async with container_context(scope=ContextScopes.INJECT):
        with pytest.raises(RuntimeError):
            await provider.async_resolve()


def test_none_scoped_provider_should_not_be_resolvable_in_named_scope_sync() -> None:
    provider = providers.ContextResource(create_sync_context_resource).with_config(scope=None)
    with container_context(scope=ContextScopes.INJECT), pytest.raises(RuntimeError):
        provider.sync_resolve()


def test_container_context_does_not_support_scope_any() -> None:
    with (
        pytest.raises(ValueError, match=f"{ContextScopes.ANY} cannot be entered!"),
    ):
        container_context(scope=ContextScopes.ANY)


def test_di_middleware_does_not_support_scope_any() -> None:
    with (
        pytest.raises(ValueError, match=f"{ContextScopes.ANY} cannot be entered!"),
    ):
        DIContextMiddleware(Mock(), scope=ContextScopes.ANY)


async def test_resource_context_does_not_reset_in_wrong_scope_async() -> None:
    class _Container(BaseContainer):
        default_scope = ContextScopes.REQUEST
        p_app = providers.ContextResource(create_async_context_resource).with_config(scope=ContextScopes.APP)
        p_request = providers.ContextResource(create_async_context_resource)

    async with container_context(scope=ContextScopes.APP):
        value_app_1 = await _Container.p_app.async_resolve()
        with pytest.raises(RuntimeError):
            await _Container.p_request.async_resolve()

        async with container_context(scope=ContextScopes.REQUEST):
            value_app_2 = await _Container.p_app.async_resolve()
            assert await _Container.p_request.async_resolve() is not None

            assert value_app_1 == value_app_2

        with pytest.raises(RuntimeError):
            await _Container.p_request.async_resolve()


def test_resource_context_does_not_set_in_wrong_scope_sync() -> None:
    class _Container(BaseContainer):
        default_scope = ContextScopes.REQUEST
        p_app = providers.ContextResource(create_sync_context_resource).with_config(scope=ContextScopes.APP)
        p_request = providers.ContextResource(create_sync_context_resource)

    with container_context(scope=ContextScopes.APP):
        value_app_1 = _Container.p_app.sync_resolve()
        with pytest.raises(RuntimeError):
            _Container.p_request.sync_resolve()

        with container_context(scope=ContextScopes.REQUEST):
            value_app_2 = _Container.p_app.sync_resolve()
            assert _Container.p_request.sync_resolve() is not None

            assert value_app_1 == value_app_2

        with pytest.raises(RuntimeError):
            _Container.p_request.sync_resolve()


async def test_strict_scope_resource_only_resolvable_in_given_scope_async() -> None:
    class _Container(BaseContainer):
        p_app = providers.ContextResource(create_async_context_resource).with_config(
            scope=ContextScopes.APP, strict_scope=True
        )
        p_request = providers.ContextResource(create_async_context_resource).with_config(
            scope=ContextScopes.REQUEST, strict_scope=True
        )

    with pytest.raises(RuntimeError):
        await _Container.p_app.async_resolve()

    with pytest.raises(InvalidContextError):
        await container_context(_Container.p_app, _Container.p_request).__aenter__()

    async with container_context(scope=ContextScopes.APP):
        assert await _Container.p_app.async_resolve() is not None
        with pytest.raises(RuntimeError):
            await _Container.p_request.async_resolve()

        async with container_context(scope=ContextScopes.REQUEST):
            assert await _Container.p_request.async_resolve() is not None
            with pytest.raises(RuntimeError):
                await _Container.p_app.async_resolve()


def test_strict_scope_resource_only_resolvable_in_given_scope_sync() -> None:
    class _Container(BaseContainer):
        p_app = providers.ContextResource(create_sync_context_resource).with_config(
            scope=ContextScopes.APP, strict_scope=True
        )
        p_request = providers.ContextResource(create_sync_context_resource).with_config(
            scope=ContextScopes.REQUEST, strict_scope=True
        )

    with pytest.raises(RuntimeError):
        _Container.p_app.sync_resolve()

    with pytest.raises(InvalidContextError):
        container_context(_Container.p_app, _Container.p_request).__enter__()

    with container_context(scope=ContextScopes.APP):
        assert _Container.p_app.sync_resolve() is not None
        with pytest.raises(RuntimeError):
            _Container.p_request.sync_resolve()

        with container_context(scope=ContextScopes.REQUEST):
            assert _Container.p_request.sync_resolve() is not None
            with pytest.raises(RuntimeError):
                _Container.p_app.sync_resolve()


def test_strict_scope_not_allowed_with_any_scope() -> None:
    with pytest.raises(ValueError, match=f"Cannot set strict_scope with scope {ContextScopes.ANY}."):
        providers.ContextResource(create_sync_context_resource).with_config(scope=ContextScopes.ANY, strict_scope=True)


async def test_async_resource_with_custom_scope() -> None:
    class MyScopes(ContextScopes):
        CUSTOM = ContextScope("CUSTOM")

    class _Container(BaseContainer):
        p_custom = providers.ContextResource(create_async_context_resource).with_config(scope=MyScopes.CUSTOM)

    assert _Container.p_custom.get_scope() == MyScopes.CUSTOM

    with pytest.raises(RuntimeError):
        await _Container.p_custom.async_resolve()

    async with container_context(_Container.p_custom, scope=MyScopes.CUSTOM):
        assert await _Container.p_custom.async_resolve() is not None


async def test_async_entering_container_context_for_all_containers_correctly_handles_named_scopes() -> None:
    class _Container(BaseContainer):
        p_app = providers.ContextResource(create_async_context_resource).with_config(scope=ContextScopes.APP)
        p_request = providers.ContextResource(create_async_context_resource).with_config(scope=ContextScopes.REQUEST)

    async with container_context(reset_all_containers=True):
        with pytest.raises(RuntimeError):
            await _Container.p_app.async_resolve()

    async with container_context(reset_all_containers=True, scope=ContextScopes.APP):
        assert await _Container.p_app.async_resolve() is not None
        with pytest.raises(RuntimeError):
            await _Container.p_request.async_resolve()

    async with container_context(reset_all_containers=True, scope=ContextScopes.REQUEST):
        assert await _Container.p_request.async_resolve() is not None
        with pytest.raises(RuntimeError):
            await _Container.p_app.async_resolve()


def test_sync_entering_container_context_for_all_containers_correctly_handles_named_scopes() -> None:
    class _Container(BaseContainer):
        p_app = providers.ContextResource(create_sync_context_resource).with_config(scope=ContextScopes.APP)
        p_request = providers.ContextResource(create_sync_context_resource).with_config(scope=ContextScopes.REQUEST)

    with container_context(reset_all_containers=True), pytest.raises(RuntimeError):
        _Container.p_app.sync_resolve()

    with container_context(reset_all_containers=True, scope=ContextScopes.APP):
        assert _Container.p_app.sync_resolve() is not None
        with pytest.raises(RuntimeError):
            _Container.p_request.sync_resolve()

    with container_context(reset_all_containers=True, scope=ContextScopes.REQUEST):
        assert _Container.p_request.sync_resolve() is not None
        with pytest.raises(RuntimeError):
            _Container.p_app.sync_resolve()


async def test_async_force_enter_context_for_scoped_resource() -> None:
    class _Container(BaseContainer):
        p_app = providers.ContextResource(create_async_context_resource).with_config(scope=ContextScopes.APP)

    async with _Container.p_app.async_context(force=True):
        assert await _Container.p_app.async_resolve() is not None

    async with _Container.async_context(force=True):
        assert await _Container.p_app.async_resolve() is not None


def test_sync_force_enter_context_for_scoped_resource() -> None:
    class _Container(BaseContainer):
        p_app = providers.ContextResource(create_sync_context_resource).with_config(scope=ContextScopes.APP)

    with _Container.p_app.sync_context(force=True):
        assert _Container.p_app.sync_resolve() is not None

    with _Container.sync_context(force=True):
        assert _Container.p_app.sync_resolve() is not None


async def test_async_force_enter_context_with_context_annotation() -> None:
    class _Container(BaseContainer):
        p_app = providers.ContextResource(create_async_context_resource).with_config(scope=ContextScopes.APP)

    @_Container.context(force=True)
    @inject(scope=None)
    async def _injected(val: str = Provide[_Container.p_app]) -> str:
        return val

    @_Container.p_app.context(force=True)
    @inject(scope=None)
    async def _injected_p(val: str = Provide[_Container.p_app]) -> str:
        return val

    assert await _injected() is not None
    assert await _injected_p() is not None


def test_sync_force_enter_context_with_context_annotation() -> None:
    class _Container(BaseContainer):
        p_app = providers.ContextResource(create_sync_context_resource).with_config(scope=ContextScopes.APP)

    @_Container.context(force=True)
    @inject(scope=None)
    def _injected(val: str = Provide[_Container.p_app]) -> str:
        return val

    @_Container.p_app.context(force=True)
    @inject(scope=None)
    def _injected_p(val: str = Provide[_Container.p_app]) -> str:
        return val

    assert _injected() is not None
    assert _injected_p() is not None


async def test_async_container_context_selects_context_items_on_entry() -> None:
    class _Container(BaseContainer):
        p_app = providers.ContextResource(create_async_context_resource).with_config(
            scope=ContextScopes.APP, strict_scope=True
        )
        p_request = providers.ContextResource(create_async_context_resource).with_config(
            scope=ContextScopes.REQUEST, strict_scope=True
        )

    async with container_context(scope=ContextScopes.APP):
        cc = container_context()

        async with container_context(scope=ContextScopes.REQUEST):
            assert get_current_scope() == ContextScopes.REQUEST
            async with cc:
                assert get_current_scope() == ContextScopes.REQUEST
                assert await _Container.p_request.async_resolve() is not None


def test_sync_container_context_selects_context_items_on_entry() -> None:
    class _Container(BaseContainer):
        p_app = providers.ContextResource(create_sync_context_resource).with_config(
            scope=ContextScopes.APP, strict_scope=True
        )
        p_request = providers.ContextResource(create_sync_context_resource).with_config(
            scope=ContextScopes.REQUEST, strict_scope=True
        )

    with container_context(scope=ContextScopes.APP):
        cc = container_context()

        with container_context(scope=ContextScopes.REQUEST):
            assert get_current_scope() == ContextScopes.REQUEST
            with cc:
                assert get_current_scope() == ContextScopes.REQUEST
                assert _Container.p_request.sync_resolve() is not None
