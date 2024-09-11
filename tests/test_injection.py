import asyncio
import datetime
import warnings

import pytest

from tests import container
from that_depends import Provide, inject


@pytest.fixture(name="fixture_one")
def create_fixture_one() -> int:
    return 1


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


def test_wrong_sync_injection() -> None:
    @inject
    def inner(
        _: container.SimpleFactory = Provide[container.DIContainer.simple_factory],
    ) -> None:
        """Do nothing."""

    with pytest.raises(RuntimeError, match="Injected arguments must not be redefined"):
        inner(_=container.SimpleFactory(dep1="1", dep2=2))


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
