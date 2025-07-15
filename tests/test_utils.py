from that_depends.utils import UNSET, Unset, is_set


def test_is_set_with_unset() -> None:
    assert not is_set(UNSET)


def test_is_set_with_value() -> None:
    assert is_set(42)
    assert is_set("hello")
    assert is_set([1, 2, 3])
    assert is_set(None)


def test_unset_is_singleton() -> None:
    assert isinstance(UNSET, Unset)
    assert UNSET is Unset()
