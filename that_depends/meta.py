import abc
import typing
from threading import Lock

from typing_extensions import override



if typing.TYPE_CHECKING:
    from that_depends.container import BaseContainer


class BaseContainerMeta(abc.ABCMeta):
    """Metaclass for BaseContainer."""

    _instances: typing.ClassVar[list[type["BaseContainer"]]] = []

    _lock: Lock = Lock()

    @override
    def __new__(cls, name: str, bases: tuple[type, ...], namespace: dict[str, typing.Any]) -> type:
        new_cls = super().__new__(cls, name, bases, namespace)
        with cls._lock:
            if name != "BaseContainer":
                cls._instances.append(new_cls)  # type: ignore[arg-type]
        return new_cls

    @classmethod
    def get_instances(cls) -> list[type["BaseContainer"]]:
        """Get all instances that inherit from BaseContainer."""
        return cls._instances

    @override
    def __setattr__(cls, key, value) -> None:
        from that_depends.providers import ContextResource
        if default_scope:= cls.__getattribute__("default_scope"):
            if isinstance(value, ContextResource):
                value = value.with_config(default_scope)
        super().__setattr__(key, value)

