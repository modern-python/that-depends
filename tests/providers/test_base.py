from typing_extensions import override

from that_depends.providers.base import AbstractProvider
from that_depends.providers.mixin import SupportsTeardown


class DummyProvider(SupportsTeardown, AbstractProvider[int]):
    """A dummy provider used for testing."""

    def __init__(self) -> None:
        super().__init__()
        self._instance: int | None = None

    @override
    async def tear_down(self, propagate: bool = True) -> None:
        self._instance = None
        if propagate:
            await self._tear_down_children()

    @override
    def sync_tear_down(self, propagate: bool = True, raise_on_async: bool = True) -> None:
        self._instance = None
        if propagate:
            self._sync_tear_down_children(raise_on_async=raise_on_async)

    @override
    async def async_resolve(self) -> int:
        self._instance = 1
        return self._instance

    @override
    def sync_resolve(self) -> int:
        self._instance = 1
        return self._instance  # pragma: no cover


def test_add_child_provider() -> None:
    provider_a = DummyProvider()
    provider_b = DummyProvider()

    assert len(provider_a._children) == 0, "Expected provider_a to have no children initially"
    provider_a.add_child_provider(provider_b)

    assert len(provider_a._children) == 1, "Expected provider_a._children to have 1 child"
    assert provider_b in provider_a._children, "provider_b should be in provider_a._children"


def test_register_with_providers() -> None:
    parent = DummyProvider()
    child_1 = DummyProvider()
    child_2 = DummyProvider()

    parent._register([child_1, child_2])

    assert parent in child_1._children, "Expected child_1._children to contain parent"
    assert parent in child_2._children, "Expected child_2._children to contain parent"


def test_register_with_mixed_items() -> None:
    parent = DummyProvider()
    child_1 = DummyProvider()
    non_provider = 12345  # not an AbstractProvider

    parent._register([child_1, non_provider])

    assert parent in child_1._children, "Expected child_1._children to contain parent"


def test_sync_tear_down_propagation() -> None:
    parent = DummyProvider()
    child_1 = DummyProvider()
    child_2 = DummyProvider()

    parent.add_child_provider(child_1)
    parent.add_child_provider(child_2)

    assert parent.sync_resolve() == 1

    assert parent._instance == 1

    parent.sync_tear_down()

    assert parent._instance is None
    assert child_1._instance is None
    assert child_2._instance is None


async def test_async_tear_down_propagation() -> None:
    parent = DummyProvider()
    child_1 = DummyProvider()
    child_2 = DummyProvider()

    parent.add_child_provider(child_1)
    parent.add_child_provider(child_2)

    assert await parent.async_resolve() == 1

    assert parent._instance == 1

    await parent.tear_down()

    assert parent._instance is None
    assert child_1._instance is None
    assert child_2._instance is None
