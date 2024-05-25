import asyncio
import datetime

import pytest

from tests import container
from that_depends import Provide, inject, inject_to_sync


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


async def test_wrong_injection() -> None:
    @inject
    async def inner(
        _: container.SimpleFactory = Provide[container.DIContainer.simple_factory],
    ) -> None:
        """Do nothing."""

    with pytest.raises(RuntimeError, match="Injected arguments must not be redefined"):
        await inner(_=container.SimpleFactory(dep1="1", dep2=2))


@inject_to_sync
def test_sync_injection(
    fixture_one: int,
    simple_factory: container.SimpleFactory = Provide[container.DIContainer.simple_factory],
    default_zero: int = 0,
) -> None:
    assert simple_factory.dep1
    assert default_zero == 0
    assert fixture_one == 1


def test_wrong_sync_injection() -> None:
    @inject_to_sync
    def inner(
        _: container.SimpleFactory = Provide[container.DIContainer.simple_factory],
    ) -> None:
        """Do nothing."""

    with pytest.raises(RuntimeError, match="Injected arguments must not be redefined"):
        inner(_=container.SimpleFactory(dep1="1", dep2=2))


def test_type_check() -> None:
    @inject
    async def main() -> None:
        pass

    asyncio.run(main())
