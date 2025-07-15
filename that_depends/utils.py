from typing import TypeGuard, TypeVar


T = TypeVar("T")


class Unset:
    """Represents an unset value."""


UNSET = Unset()


def is_set(value: T | Unset) -> TypeGuard[T]:
    """Check if a value is set (not UNSET)."""
    return value is not UNSET
