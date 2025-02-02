import abc
import typing
from collections.abc import MutableMapping
from threading import Lock

from typing_extensions import override


if typing.TYPE_CHECKING:
    from that_depends.container import BaseContainer


class DefaultScopeNotDefinedError(Exception):
    """Exception raised when default_scope is not defined."""


class _ContainerMetaDict(dict[str, typing.Any]):
    """Implements custom logic for the container metaclass."""

    @override
    def __setitem__(self, key: str, value: typing.Any) -> None:
        from that_depends.providers.context_resources import ContextResource, ContextScopes

        if isinstance(value, ContextResource) and value.get_scope() == ContextScopes.ANY:
            try:
                default_scope = self.__getitem__("default_scope")
                super().__setitem__(key, value.with_config(default_scope))
            except KeyError as e:
                msg = "Explicitly define default_scope before defining ContextResource providers."
                raise DefaultScopeNotDefinedError(msg) from e
        else:
            super().__setitem__(key, value)


class BaseContainerMeta(abc.ABCMeta):
    """Metaclass for BaseContainer."""

    _instances: typing.ClassVar[dict[str, type["BaseContainer"]]] = {}

    _MUTABLE_ATTRS = (
        "__abstractmethods__",
        "__parameters__",
        "_abc_impl",
        "providers",
        "containers",
    )

    _lock: Lock = Lock()

    def name(cls) -> str:
        """Get the name of the container class."""
        if alias := getattr(cls, "alias", None):
            return typing.cast(str, alias)
        return cls.__name__

    @classmethod
    @override
    def __prepare__(cls, name: str, bases: tuple[type, ...], /, **kwds: typing.Any) -> MutableMapping[str, object]:
        return _ContainerMetaDict()

    @override
    def __new__(cls, name: str, bases: tuple[type, ...], namespace: dict[str, typing.Any]) -> type:
        new_cls = super().__new__(cls, name, bases, namespace)
        cls_name = new_cls.name()
        with cls._lock:
            if name != "BaseContainer":
                cls._instances[cls_name] = typing.cast(type["BaseContainer"], new_cls)
        return new_cls

    @classmethod
    def get_instances(cls) -> dict[str, type["BaseContainer"]]:
        """Get all instances that inherit from BaseContainer."""
        return cls._instances

    @override
    def __setattr__(cls, key: str, value: typing.Any) -> None:
        if key in cls._MUTABLE_ATTRS:  # Allow modification of mutable attributes
            super().__setattr__(key, value)
        else:
            msg = f"Cannot add new attribute '{key}' to class '{cls.__name__}'"
            raise AttributeError(msg)
