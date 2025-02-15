import abc
import typing
from abc import abstractmethod
from contextlib import contextmanager
from contextvars import ContextVar, Token

from typing_extensions import override


class InvalidContextError(RuntimeError):
    """Raised when an invalid context is being used."""


class ContextScope:
    """A named context scope."""

    def __init__(self, name: str) -> None:
        """Initialize a new context scope."""
        self._name = name

    @property
    def name(self) -> str:
        """Get the name of the context scope."""
        return self._name

    @override
    def __eq__(self, other: object) -> bool:
        if isinstance(other, ContextScope):
            return self.name == other.name
        return False

    @override
    def __repr__(self) -> str:
        return f"{self.name!r}"


class ContextScopes:
    """Enumeration of context scopes."""

    ANY = ContextScope("ANY")  # special scope that can be used in any context
    APP = ContextScope("APP")  # application scope
    REQUEST = ContextScope("REQUEST")  # request scope
    INJECT = ContextScope("INJECT")  # inject scope


_CONTAINER_SCOPE: typing.Final[ContextVar[ContextScope | None]] = ContextVar("__CONTAINER_SCOPE__", default=None)


def get_current_scope() -> ContextScope | None:
    """Get the current context scope.

    Returns:
        ContextScope | None: The current context scope.

    """
    return _CONTAINER_SCOPE.get()


def _set_current_scope(scope: ContextScope | None) -> Token[ContextScope | None]:
    return _CONTAINER_SCOPE.set(scope)


@contextmanager
def _enter_named_scope(scope: ContextScope) -> typing.Iterator[ContextScope]:
    token = _set_current_scope(scope)
    yield scope
    _CONTAINER_SCOPE.reset(token)


T = typing.TypeVar("T")
CT = typing.TypeVar("CT")


class SupportsContext(typing.Generic[CT], abc.ABC):
    """Interface for resources that support context initialization.

    This interface defines methods to create synchronous and asynchronous
    context managers, as well as a function decorator for context initialization.
    """

    @abstractmethod
    def get_scope(self) -> ContextScope | None:
        """Return the scope of the resource."""

    @abstractmethod
    def async_context(self, force: bool = False) -> typing.AsyncContextManager[CT]:
        """Create an async context manager for this resource.

        Args:
            force (bool): If True, the context will be entered regardless of the current scope.

        Returns:
            AsyncContextManager[CT]: An async context manager.

        Example:
            ```python
            async with my_resource.async_context():
                result = await my_resource.async_resolve()
            ```

        """

    @abstractmethod
    def sync_context(self, force: bool = False) -> typing.ContextManager[CT]:
        """Create a sync context manager for this resource.

        Args:
            force (bool): If True, the context will be entered regardless of the current scope.

        Returns:
            ContextManager[CT]: A sync context manager.

        Example:
            ```python
            with my_resource.sync_context():
                result = my_resource.sync_resolve()
            ```

        """

    @abstractmethod
    def supports_sync_context(self) -> bool:
        """Check whether the resource supports sync context.

        Returns:
            bool: True if sync context is supported, False otherwise.

        """
