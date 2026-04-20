from that_depends import ContextScopes
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
