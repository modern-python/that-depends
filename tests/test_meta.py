import typing

import pytest

from that_depends import BaseContainer, ContextScopes, providers
from that_depends.exceptions import TypeNotBoundError
from that_depends.meta import BaseContainerMeta


def test_base_container_meta_has_correct_default_scope() -> None:
    class _Test(metaclass=BaseContainerMeta):
        pass

    assert _Test.get_scope() == ContextScopes.ANY


def test_base_container_meta_uses_explicit_default_scope() -> None:
    class _Test(metaclass=BaseContainerMeta):
        default_scope = ContextScopes.INJECT

    assert _Test.get_scope() == ContextScopes.INJECT


def test_base_container_meta_has_correct_default_name() -> None:
    class _Test(metaclass=BaseContainerMeta):
        pass

    assert _Test.name() == "_Test"


def test_type_provider_cache_invalidates_after_rebinding() -> None:
    provider = providers.Object(1).bind(int)

    class Container(BaseContainer):
        value = provider

    assert Container.get_provider_for_type(int) is provider

    provider.bind(str)

    with pytest.raises(TypeNotBoundError):
        Container.get_provider_for_type(int)
    assert Container.get_provider_for_type(str) is typing.cast(providers.Object[str], provider)
