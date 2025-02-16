import abc
import typing
import warnings
from collections.abc import MutableMapping
from contextlib import AsyncExitStack, ExitStack, asynccontextmanager, contextmanager
from threading import Lock
from typing import TYPE_CHECKING

from typing_extensions import override

from that_depends.providers import AbstractProvider
from that_depends.providers.context_resources import ContextResource, ContextScope, ContextScopes, SupportsContext


if TYPE_CHECKING:
    from that_depends import BaseContainer  # pragma: no cover


class DefaultScopeNotDefinedError(Exception):
    """Exception raised when default_scope is not defined."""


class _ContainerMetaDict(dict[str, typing.Any]):
    """Implements custom logic for the container metaclass."""

    @override
    def __setitem__(self, key: str, value: typing.Any) -> None:
        if isinstance(value, ContextResource) and value.get_scope() == ContextScopes.ANY:
            try:
                default_scope = self.__getitem__("default_scope")
                super().__setitem__(key, value.with_config(default_scope))
            except KeyError as e:
                msg = "Explicitly define default_scope before defining ContextResource providers."
                raise DefaultScopeNotDefinedError(msg) from e
        else:
            super().__setitem__(key, value)


class BaseContainerMeta(SupportsContext[None], abc.ABCMeta):
    """Metaclass for BaseContainer."""

    @override
    def get_scope(cls) -> ContextScope | None:
        if scope := getattr(cls, "default_scope", None):
            return typing.cast(ContextScope | None, scope)
        return ContextScopes.ANY

    @asynccontextmanager
    @override
    async def async_context(cls, force: bool = False) -> typing.AsyncIterator[None]:
        async with AsyncExitStack() as stack:
            for container in cls.get_containers():
                await stack.enter_async_context(container.async_context(force=force))
            for provider in cls.get_providers().values():
                if isinstance(provider, ContextResource):
                    await stack.enter_async_context(provider.async_context(force=force))
            yield

    @contextmanager
    @override
    def sync_context(cls, force: bool = False) -> typing.Iterator[None]:
        with ExitStack() as stack:
            for container in cls.get_containers():
                stack.enter_context(container.sync_context(force=force))
            for provider in cls.get_providers().values():
                if isinstance(provider, ContextResource) and not provider._is_async:  # noqa: SLF001
                    stack.enter_context(provider.sync_context(force=force))
            yield

    @override
    def supports_sync_context(cls) -> bool:
        return True

    _instances: typing.ClassVar[dict[str, type["BaseContainer"]]] = {}

    _MUTABLE_ATTRS = (
        "__abstractmethods__",
        "__parameters__",
        "_abc_impl",
        "providers",
        "containers",
        "alias",
        "default_scope",
    )

    _lock: Lock = Lock()
    alias: str | None

    def __init__(cls, name: str, bases: tuple[type, ...], namespace: dict[str, typing.Any]) -> None:
        """Initialize the container class."""
        super().__init__(name, bases, namespace)
        cls_name = cls.name()
        with cls._lock:
            if name != "BaseContainer":
                if cls_name in cls._instances:
                    warnings.warn(f"Overwriting container '{cls_name}'", UserWarning, stacklevel=2)
                cls._instances[cls_name] = typing.cast(type["BaseContainer"], cls)

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
        return super().__new__(cls, name, bases, namespace)

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

    def get_providers(cls) -> dict[str, "AbstractProvider[typing.Any]"]:
        """Get all connected providers."""
        if not hasattr(cls, "providers"):
            cls.providers = {k: v for k, v in cls.__dict__.items() if isinstance(v, AbstractProvider)}
        return cls.providers

    def get_containers(cls) -> list[type["BaseContainer"]]:
        """Get all connected containers."""
        if not hasattr(cls, "containers"):
            cls.containers: list[type[BaseContainer]] = []

        return cls.containers
