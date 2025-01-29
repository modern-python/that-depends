import asyncio
import datetime
import typing
import warnings

import pytest

from tests import container
from that_depends import BaseContainer, Provide, inject, providers
from that_depends.providers.context_resources import ContextScopes


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
