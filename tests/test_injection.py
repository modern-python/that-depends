import pytest

from tests import container
from that_depends import inject


@pytest.fixture(name="fixture_one")
def create_fixture_one() -> int:
    return 1


@pytest.mark.asyncio()
@inject
async def test_injection(
    fixture_one: int,
    independent_factory: container.IndependentFactory = container.DIContainer.independent_factory.lazy,
    async_dependent_factory: container.AsyncDependentFactory = container.DIContainer.async_dependent_factory.lazy,
    default_zero: int = 0,
) -> None:
    assert independent_factory.dep1
    assert async_dependent_factory.async_resource == "async resource"
    assert True
    assert default_zero == 0
    assert fixture_one == 1
