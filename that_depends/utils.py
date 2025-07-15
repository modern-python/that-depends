from typing import Any, ClassVar, TypeGuard, TypeVar


T = TypeVar("T")


class _Singleton(type):
    _instances: ClassVar[dict[type, Any]] = {}

    def __call__(cls, *args: Any, **kwargs: Any) -> Any:  # noqa: ANN401
        if cls not in cls._instances:
            cls._instances[cls] = super().__call__(*args, **kwargs)
        return cls._instances[cls]


class Unset(metaclass=_Singleton):
    """Represents an unset value."""


UNSET = Unset()


def is_set(value: T | Unset) -> TypeGuard[T]:
    """Check if a value is set (not UNSET)."""
    return value is not UNSET
