import dataclasses

import pytest

from tests import container
from tests.container import DIContainer


@dataclasses.dataclass(kw_only=True, slots=True)
class WrongFactory:
    some_dep: int = 1
    not_existing_name: container.DependentFactory
    sync_resource: str


async def test_dependency_resolver() -> None:
    resolver = DIContainer.resolver(container.FreeFactory)
    dep1 = await resolver()
    dep2 = await DIContainer.resolve(container.FreeFactory)

    assert dep1
    assert dep2
    assert dep1 is not dep2


async def test_dependency_resolver_failed() -> None:
    resolver = DIContainer.resolver(WrongFactory)
    with pytest.raises(RuntimeError, match="Provider is not found, field_name='not_existing_name'"):
        await resolver()
