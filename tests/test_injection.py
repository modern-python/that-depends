import pytest

from tests import container
from that_depends import Provide, inject


@pytest.fixture(name="fixture_one")
def create_fixture_one() -> int:
    return 1


@inject
async def test_injection(
    fixture_one: int,
    independent_factory: container.IndependentFactory = Provide[container.DIContainer.independent_factory],
    async_dependent_factory: container.AsyncDependentFactory = Provide[container.DIContainer.async_dependent_factory],
    default_zero: int = 0,
) -> None:
    assert independent_factory.dep1
    assert async_dependent_factory.async_resource == "async resource"
    assert True
    assert default_zero == 0
    assert fixture_one == 1


async def test_wrong_injection() -> None:
    @inject
    async def inner(
        _: container.IndependentFactory = Provide[container.DIContainer.independent_factory],
    ) -> None:
        """Do nothing."""

    with pytest.raises(RuntimeError, match="Injected arguments must not be redefined"):
        await inner(_=container.IndependentFactory(dep1="1", dep2=2))
