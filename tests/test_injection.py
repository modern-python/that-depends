import asyncio
import datetime
import random
import typing
import warnings
from unittest.mock import Mock

import pytest

from tests import container
from that_depends import BaseContainer, ContextScopes, Provide, inject, providers
from that_depends.injection import StringProviderDefinition


@pytest.fixture(name="fixture_one")
def create_fixture_one() -> int:
    return 1


async def _async_creator() -> typing.AsyncIterator[int]:
    yield 1


def _sync_creator() -> typing.Iterator[int]:
    yield 1


@inject
async def test_injection(
    fixture_one: int,
    simple_factory: container.SimpleFactory = Provide[container.DIContainer.simple_factory],
    dependent_factory: container.DependentFactory = Provide[container.DIContainer.dependent_factory],
    default_zero: int = 0,
) -> None:
    assert simple_factory.dep1
    assert isinstance(dependent_factory.async_resource, datetime.datetime)
    assert default_zero == 0
    assert fixture_one == 1


async def test_injection_with_overriding() -> None:
    @inject
    async def inner(
        arg1: bool,
        arg2: container.SimpleFactory = Provide[container.DIContainer.simple_factory],
    ) -> None:
        _ = arg1
        original_obj = await container.DIContainer.simple_factory()
        assert arg2.dep1 != original_obj.dep1
        assert arg2.dep2 != original_obj.dep2

    await inner(arg1=True, arg2=container.SimpleFactory(dep1="1", dep2=2))
    await inner(True, container.SimpleFactory(dep1="1", dep2=2))
    await inner(True, arg2=container.SimpleFactory(dep1="1", dep2=2))


async def test_empty_injection() -> None:
    @inject
    async def inner(_: int) -> None:
        """Do nothing."""

    warnings.filterwarnings("error")

    with pytest.raises(RuntimeWarning, match="Expected injection, but nothing found. Remove @inject decorator."):
        await inner(1)


@inject
def test_sync_injection(
    fixture_one: int,
    simple_factory: container.SimpleFactory = Provide[container.DIContainer.simple_factory],
    default_zero: int = 0,
) -> None:
    assert simple_factory.dep1
    assert default_zero == 0
    assert fixture_one == 1


def test_overriden_sync_injection() -> None:
    @inject
    def inner(
        _: container.SimpleFactory = Provide[container.DIContainer.simple_factory],
    ) -> container.SimpleFactory:
        """Do nothing."""
        return _

    factory = container.SimpleFactory(dep1="1", dep2=2)
    assert inner(_=factory) == factory


def test_sync_empty_injection() -> None:
    @inject
    def inner(_: int) -> None:
        """Do nothing."""

    warnings.filterwarnings("error")

    with pytest.raises(RuntimeWarning, match="Expected injection, but nothing found. Remove @inject decorator."):
        inner(1)


def test_type_check() -> None:
    @inject
    async def main(simple_factory: container.SimpleFactory = Provide[container.DIContainer.simple_factory]) -> None:
        assert simple_factory

    asyncio.run(main())


async def test_async_injection_with_scope() -> None:
    class _Container(BaseContainer):
        default_scope = ContextScopes.ANY
        async_resource = providers.ContextResource(_async_creator).with_config(scope=ContextScopes.INJECT)

    async def _injected(val: int = Provide[_Container.async_resource]) -> int:
        return val

    assert await inject(scope=ContextScopes.INJECT)(_injected)() == 1
    assert await inject(_injected)() == 1
    with pytest.raises(RuntimeError):
        await inject(scope=None)(_injected)()
    with pytest.raises(RuntimeError):
        await inject(scope=ContextScopes.REQUEST)(_injected)()


async def test_sync_injection_with_scope() -> None:
    class _Container(BaseContainer):
        default_scope = ContextScopes.ANY
        p_inject = providers.ContextResource(_sync_creator).with_config(scope=ContextScopes.INJECT)

    def _injected(val: int = Provide[_Container.p_inject]) -> int:
        return val

    assert inject(scope=ContextScopes.INJECT)(_injected)() == 1
    assert inject(_injected)() == 1
    with pytest.raises(RuntimeError):
        inject(scope=None)(_injected)()
    with pytest.raises(RuntimeError):
        inject(scope=ContextScopes.REQUEST)(_injected)()


def test_inject_decorator_should_not_allow_any_scope() -> None:
    with pytest.raises(ValueError, match=f"{ContextScopes.ANY} is not allowed in inject decorator."):
        inject(scope=ContextScopes.ANY)


@pytest.mark.parametrize(
    ("definition", "expected"),
    [
        ("container.provider", ("container", "provider", [])),
        ("container.provider.attr", ("container", "provider", ["attr"])),
        ("container.provider.attr1.attr2", ("container", "provider", ["attr1", "attr2"])),
        ("some.long.container.provider", ("some", "long", ["container", "provider"])),
    ],
)
def test_validate_and_extract_provider_definition_valid(definition: str, expected: tuple[str, str, list[str]]) -> None:
    """Test valid definitions and ensure the function returns the correct tuple."""
    parsed_definition = StringProviderDefinition(definition)
    result = parsed_definition._container_name, parsed_definition._provider_name, parsed_definition._attrs
    assert result == expected


@pytest.mark.parametrize(
    "definition",
    [
        "",
        "container",
        ".provider",
        "container.",
        "container..provider",
        "container.provider.",
    ],
)
def test_validate_and_extract_provider_definition_invalid(definition: str) -> None:
    """Test invalid definitions and ensure the function raises ValueError."""
    with pytest.raises(ValueError, match=f"Invalid provider definition: {definition}"):
        StringProviderDefinition(definition)


async def test_async_injection_with_string_provider_definition() -> None:
    return_value = 321321

    class _Container(BaseContainer):
        async_resource = providers.Factory(lambda: return_value)

    @inject
    async def _injected(val: int = Provide["_Container.async_resource"]) -> int:
        return val

    assert await _injected() == return_value


def test_sync_injection_with_string_provider_definition() -> None:
    return_value = 312312421

    class _Container(BaseContainer):
        sync_resource = providers.Factory(lambda: return_value)

    @inject
    def _injected(val: int = Provide["_Container.sync_resource"]) -> int:
        return val

    assert _injected() == return_value


def test_provider_string_definition_with_alias() -> None:
    return_value = 321

    class _Container(BaseContainer):
        alias = "ALIAS"
        sync_resource = providers.Factory(lambda: return_value)

    @inject
    def _injected(val: int = Provide["ALIAS.sync_resource"]) -> int:
        return val

    assert _injected() == return_value


def test_provider_string_definition_with_attr_getter() -> None:
    expected_value = 123123
    return_value = Mock()
    return_value.a = expected_value

    class _Container(BaseContainer):
        sync_resource = providers.Factory(lambda: return_value)

    @inject
    def _injected(val: int = Provide["_Container.sync_resource.a"]) -> int:
        return val

    assert _injected() == expected_value


def test_inject_with_non_existing_container() -> None:
    provider_name = "DOESNOTEXIST"

    @inject
    def _injected(val: int = Provide[f"{provider_name}.provider"]) -> None: ...

    with pytest.raises(ValueError, match=f"Container {provider_name} not found in scope!"):
        _injected()


def test_inject_with_non_existing_provider() -> None:
    container_alias = "EXIST"

    class _Container(BaseContainer):
        alias = container_alias

    provider_name = "DOESNOTEXIST"

    @inject
    def _injected(val: int = Provide[f"EXIST.{provider_name}"]) -> None: ...

    with pytest.raises(ValueError, match=f"Provider {provider_name} not found in container {container_alias}"):
        _injected()


def test_provider_resolution_with_string_definition_happens_at_runtime() -> None:
    return_value = 321

    @inject
    def _injected(val: int = Provide["_Container.sync_resource"]) -> int:
        return val

    class _Container(BaseContainer):
        sync_resource = providers.Factory(lambda: return_value)

    assert _injected() == return_value


async def test_inject_does_not_initialize_context_async() -> None:
    return_value = 3.0

    async def _async_resource() -> typing.AsyncIterator[float]:
        yield return_value

    class _Container(BaseContainer):
        provider_used = providers.ContextResource(_async_resource).with_config(scope=ContextScopes.INJECT)
        provider_unused = providers.ContextResource(_async_resource).with_config(scope=ContextScopes.INJECT)

    @inject
    async def _injected(v: float = Provide[_Container.provider_used]) -> float:
        with pytest.raises(RuntimeError):
            assert await _Container.provider_unused.resolve()

        assert isinstance(v, float)
        assert v == await _Container.provider_used.resolve()
        return v

    assert await _injected() == return_value

    with pytest.raises(RuntimeError):
        assert await _Container.provider_used.resolve()


def test_inject_does_not_initialize_context_sync() -> None:
    return_value = 3.0

    def _sync_resource() -> typing.Iterator[float]:
        yield return_value

    class _Container(BaseContainer):
        provider_used = providers.ContextResource(_sync_resource).with_config(scope=ContextScopes.INJECT)
        provider_unused = providers.ContextResource(_sync_resource).with_config(scope=ContextScopes.INJECT)

    @inject
    def _injected(v: float = Provide[_Container.provider_used]) -> float:
        with pytest.raises(RuntimeError):
            assert _Container.provider_unused.resolve_sync()
        assert isinstance(v, float)
        assert v == _Container.provider_used.resolve_sync()
        return v

    assert _injected() == return_value

    with pytest.raises(RuntimeError):
        assert _Container.provider_used.resolve_sync()


async def test_injection_initializes_context_for_parents_async() -> None:
    async def _async_resource() -> typing.AsyncIterator[float]:
        yield random.random()

    async def _async_resource_dependent(v: float) -> typing.AsyncIterator[float]:
        yield v

    class _Container(BaseContainer):
        grandparent_used = providers.ContextResource(_async_resource).with_config(scope=ContextScopes.INJECT)
        parent_used = providers.ContextResource(_async_resource_dependent, grandparent_used.cast).with_config(
            scope=ContextScopes.INJECT
        )
        provider_used = providers.ContextResource(_async_resource_dependent, parent_used.cast).with_config(
            scope=ContextScopes.INJECT
        )
        provider_unused = providers.ContextResource(_async_resource).with_config(scope=ContextScopes.INJECT)

    @inject
    async def _injected(v: float = Provide[_Container.provider_used]) -> float:
        with pytest.raises(RuntimeError):
            assert await _Container.provider_unused.resolve()
        assert isinstance(v, float)
        assert v == await _Container.provider_used.resolve()
        assert v == await _Container.parent_used.resolve()
        assert v == await _Container.grandparent_used.resolve()
        return v

    assert isinstance(await _injected(), float)
    with pytest.raises(RuntimeError):
        await _Container.provider_used.resolve()
    with pytest.raises(RuntimeError):
        await _Container.parent_used.resolve()
    with pytest.raises(RuntimeError):
        await _Container.grandparent_used.resolve()
    with pytest.raises(RuntimeError):
        await _Container.provider_unused.resolve()


def test_injection_initializes_context_for_parents_sync() -> None:
    def _sync_resource() -> typing.Iterator[float]:
        yield random.random()

    def _sync_resource_dependent(v: float) -> typing.Iterator[float]:
        yield v

    class _Container(BaseContainer):
        grandparent_used = providers.ContextResource(_sync_resource).with_config(scope=ContextScopes.INJECT)
        parent_used = providers.ContextResource(_sync_resource_dependent, grandparent_used.cast).with_config(
            scope=ContextScopes.INJECT
        )
        provider_used = providers.ContextResource(_sync_resource_dependent, parent_used.cast).with_config(
            scope=ContextScopes.INJECT
        )
        provider_unused = providers.ContextResource(_sync_resource).with_config(scope=ContextScopes.INJECT)

    @inject
    def _injected(v: float = Provide[_Container.provider_used]) -> float:
        with pytest.raises(RuntimeError):
            assert _Container.provider_unused.resolve_sync()
        assert isinstance(v, float)
        assert v == _Container.provider_used.resolve_sync()
        assert v == _Container.parent_used.resolve_sync()
        assert v == _Container.grandparent_used.resolve_sync()
        return v

    assert isinstance(_injected(), float)
    with pytest.raises(RuntimeError):
        _Container.provider_used.resolve_sync()
    with pytest.raises(RuntimeError):
        _Container.parent_used.resolve_sync()
    with pytest.raises(RuntimeError):
        _Container.grandparent_used.resolve_sync()
    with pytest.raises(RuntimeError):
        _Container.provider_unused.resolve_sync()


async def test_injection_initializes_context_for_parents_only_once_async() -> None:
    async def _async_resource() -> typing.AsyncIterator[float]:
        yield random.random()

    async def _async_resource_dependent(v: float) -> typing.AsyncIterator[float]:
        yield v

    class _Container(BaseContainer):
        grandparent = providers.ContextResource(_async_resource).with_config(scope=ContextScopes.REQUEST)
        parent = providers.ContextResource(_async_resource_dependent, grandparent.cast).with_config(
            scope=ContextScopes.REQUEST
        )
        provider = providers.ContextResource(_async_resource_dependent, parent.cast).with_config(
            scope=ContextScopes.REQUEST
        )
        provider_with_same_parent = providers.ContextResource(_async_resource_dependent, parent.cast).with_config(
            scope=ContextScopes.REQUEST
        )

    @inject(scope=ContextScopes.REQUEST)
    async def _injected(
        v_1: float = Provide[_Container.provider], v_2: float = Provide[_Container.provider_with_same_parent]
    ) -> float:
        assert isinstance(v_1, float)
        assert isinstance(v_2, float)
        assert v_1 == await _Container.provider.resolve()
        assert v_1 == await _Container.parent.resolve()
        assert v_1 == await _Container.grandparent.resolve()
        assert v_1 == v_2
        return v_1 + v_2

    assert isinstance(await _injected(), float)


def test_injection_initializes_context_for_parents_only_once_sync() -> None:
    def _sync_resource() -> typing.Iterator[float]:
        yield random.random()

    def _sync_resource_dependent(v: float) -> typing.Iterator[float]:
        yield v

    class _Container(BaseContainer):
        default_scope = ContextScopes.APP
        grandparent = providers.ContextResource(_sync_resource).with_config(scope=ContextScopes.ANY)
        parent = providers.ContextResource(_sync_resource_dependent, grandparent.cast).with_config(
            scope=ContextScopes.APP
        )
        provider = providers.ContextResource(_sync_resource_dependent, parent.cast).with_config(scope=ContextScopes.APP)
        provider_with_same_parent = providers.ContextResource(_sync_resource_dependent, parent.cast).with_config(
            scope=ContextScopes.APP
        )

    @inject(scope=ContextScopes.APP)
    def _injected(
        v_1: float = Provide[_Container.provider], v_2: float = Provide[_Container.provider_with_same_parent]
    ) -> float:
        assert isinstance(v_1, float)
        assert isinstance(v_2, float)
        assert v_1 == _Container.provider.resolve_sync()
        assert v_1 == _Container.parent.resolve_sync()
        assert v_1 == _Container.grandparent.resolve_sync()
        assert v_1 == v_2
        return v_1 + v_2

    assert isinstance(_injected(), float)


async def test_inject_scope_does_not_init_context_for_out_of_scope_dependents_async() -> None:
    async def _async_resource() -> typing.AsyncIterator[float]:
        yield random.random()

    class _Container(BaseContainer):
        parent = providers.ContextResource(_async_resource).with_config(scope=ContextScopes.INJECT)
        child = providers.Factory(lambda x: x, parent.cast)

    @inject(scope=ContextScopes.APP)
    async def _injected(v: float = Provide[_Container.child]) -> float:
        return v

    with pytest.raises(RuntimeError):
        await _injected()

    async with _Container.parent.context_async(force=True):
        parent_value = await _Container.parent.resolve()
        assert await _injected() == parent_value


async def test_inject_scope_does_not_init_context_for_out_of_scope_dependents_sync() -> None:
    def _sync_resource() -> typing.Iterator[float]:
        yield random.random()

    class _Container(BaseContainer):
        parent = providers.ContextResource(_sync_resource).with_config(scope=ContextScopes.INJECT)
        child = providers.Factory(lambda x: x, parent.cast)

    @inject(scope=ContextScopes.APP)
    def _injected(v: float = Provide[_Container.child]) -> float:
        return v

    with pytest.raises(RuntimeError):
        _injected()

    with _Container.parent.context_sync(force=True):
        parent_value = _Container.parent.resolve_sync()
        assert _injected() == parent_value
