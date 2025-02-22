import typing
from collections.abc import Callable

import pytest
from typing_extensions import override

from that_depends.providers import (
    AsyncFactory,
    AsyncSingleton,
    Dict,
    Factory,
    List,
    Object,
    Resource,
    Selector,
    Singleton,
    ThreadLocalSingleton,
)
from that_depends.providers.base import AbstractProvider
from that_depends.providers.context_resources import ContextResource
from that_depends.providers.mixin import SupportsTeardown


class DummyProvider(SupportsTeardown, AbstractProvider[int]):
    """A dummy provider used for testing."""

    def __init__(self) -> None:
        super().__init__()
        self._instance: int | None = None

    @override
    async def tear_down(self) -> None:
        self._instance = None
        await self._tear_down_children()

    @override
    def sync_tear_down(self) -> None:
        self._instance = None
        self._sync_tear_down_children()

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


CHILD_PROVIDER = Object(999)
T = typing.TypeVar("T")


def _sync_iter(x: T) -> typing.Iterator[T]:
    yield x  # pragma: no cover


@pytest.mark.parametrize(
    ("constructor", "expected_registration"),
    [
        (lambda child: Object(child), False),
        (lambda child: Factory(lambda x: x, child), True),
        (lambda child: Factory(lambda provider: provider, provider=child), True),
        (lambda child: AsyncFactory(lambda x: x, child), True),
        (lambda child: AsyncFactory(lambda provider: provider, provider=child), True),
        (lambda child: Singleton(lambda x: x, child), True),
        (lambda child: AsyncSingleton(lambda x: x, child), True),
        (lambda child: ThreadLocalSingleton(lambda x: x, child), True),
        (lambda child: Resource(_sync_iter, child), True),
        (
            lambda child: ContextResource(
                _sync_iter,
                child,
            ),
            True,
        ),
        (lambda child: List(child), True),
        (lambda child: List(child, Object(123)), True),
        (lambda child: Dict(main=child), True),
        (lambda child: Dict(main=child, other=Object("test")), True),
        (lambda child: Selector("local", the_child=child), True),
        (lambda child: Selector(child, local=Object(123)), False),
    ],
)
def test_provider_registration(
    constructor: Callable[..., AbstractProvider[typing.Any]], expected_registration: bool
) -> None:
    child = Object(999)
    parent = constructor(child)
    actual = parent in child._children

    if expected_registration:
        assert actual, f"Expected {parent} to be in child._children but got child._children={child._children}"
    else:
        assert not actual, f"Did NOT expect registration, but found {parent} in child._children={child._children}"


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
