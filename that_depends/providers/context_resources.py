import abc
import asyncio
import contextlib
import inspect
import logging
import threading
import typing
from abc import abstractmethod
from contextlib import AbstractAsyncContextManager, AbstractContextManager, contextmanager
from contextvars import ContextVar, Token
from functools import wraps
from types import TracebackType
from typing import Final, overload

from typing_extensions import TypeIs, override

from that_depends.entities.resource_context import ResourceContext
from that_depends.meta import BaseContainerMeta
from that_depends.providers.base import AbstractResource


if typing.TYPE_CHECKING:
    from that_depends.container import BaseContainer


logger: typing.Final = logging.getLogger(__name__)
T_co = typing.TypeVar("T_co", covariant=True)
P = typing.ParamSpec("P")
_CONTAINER_CONTEXT: typing.Final[ContextVar[dict[str, typing.Any]]] = ContextVar("__CONTAINER_CONTEXT__")

AppType = typing.TypeVar("AppType")
Scope = typing.MutableMapping[str, typing.Any]
Message = typing.MutableMapping[str, typing.Any]
Receive = typing.Callable[[], typing.Awaitable[Message]]
Send = typing.Callable[[Message], typing.Awaitable[None]]
ASGIApp = typing.Callable[[Scope, Receive, Send], typing.Awaitable[None]]
_ASYNC_CONTEXT_KEY: typing.Final[str] = "__ASYNC_CONTEXT__"

ContextType = dict[str, typing.Any]


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


def _get_container_context() -> dict[str, typing.Any]:
    try:
        return _CONTAINER_CONTEXT.get()
    except LookupError as exc:
        msg = "Context is not set. Use container_context"
        raise RuntimeError(msg) from exc


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


def fetch_context_item(key: str, default: typing.Any = None) -> typing.Any:  # noqa: ANN401
    """Retrieve a value from the global context.

    Args:
        key (str): The key to retrieve from the global context.
        default (Any): The default value to return if the key is not found.

    Returns:
        Any: The value associated with the key in the global context or the default value.

    Example:
        ```python
        async with container_context(global_context={"username": "john_doe"}):
            user = fetch_context_item("username")
        ```

    """
    return _get_container_context().get(key, default)


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


class ContextResource(
    AbstractResource[T_co],
    SupportsContext[ResourceContext[T_co]],
):
    """A context-dependent provider that resolves resources only if their context is initialized.

    `ContextResource` handles both synchronous and asynchronous resource creators
    and ensures they are properly torn down when the context exits.
    """

    @override
    async def async_resolve(self) -> T_co:
        current_scope = get_current_scope()
        if not self._strict_scope or self._scope in (ContextScopes.ANY, current_scope):
            return await super().async_resolve()
        msg = f"Cannot resolve resource with scope `{self._scope}` in scope `{current_scope}`"
        raise RuntimeError(msg)

    @override
    def sync_resolve(self) -> T_co:
        current_scope = get_current_scope()
        if not self._strict_scope or self._scope in (ContextScopes.ANY, current_scope):
            return super().sync_resolve()
        msg = f"Cannot resolve resource with scope `{self._scope}` in scope `{current_scope}`"
        raise RuntimeError(msg)

    @override
    def get_scope(self) -> ContextScope | None:
        return self._scope

    __slots__ = (
        "_args",
        "_context",
        "_creator",
        "_internal_name",
        "_kwargs",
        "_override",
        "_scope",
        "_token",
        "is_async",
    )

    def __init__(
        self,
        creator: typing.Callable[P, typing.Iterator[T_co] | typing.AsyncIterator[T_co]],
        *args: P.args,
        **kwargs: P.kwargs,
    ) -> None:
        """Initialize a new context resource.

        Args:
            creator (Callable[P, Iterator[T_co] | AsyncIterator[T_co]]):
                A sync or async iterator that yields the resource to be provided.
            *args (P.args): Positional arguments to pass to the creator.
            **kwargs (P.kwargs): Keyword arguments to pass to the creator.

        """
        super().__init__(creator, *args, **kwargs)
        self._from_creator = creator
        self._context: ContextVar[ResourceContext[T_co]] = ContextVar(f"{self._creator.__name__}-context")
        self._token: Token[ResourceContext[T_co]] | None = None
        self._async_lock: Final = asyncio.Lock()
        self._lock: Final = threading.Lock()
        self._scope: ContextScope | None = ContextScopes.ANY
        self._strict_scope: bool = False

    @overload
    def context(self, func: typing.Callable[P, T]) -> typing.Callable[P, T]: ...

    @overload
    def context(self, *, force: bool = False) -> typing.Callable[[typing.Callable[P, T]], typing.Callable[P, T]]: ...

    def context(
        self, func: typing.Callable[P, T] | None = None, force: bool = False
    ) -> typing.Callable[P, T] | typing.Callable[[typing.Callable[P, T]], typing.Callable[P, T]]:
        """Create a new context manager for the resource, the context manager will be async if the resource is async.

        Returns:
            typing.ContextManager[ResourceContext[T_co]] | typing.AsyncContextManager[ResourceContext[T_co]]:
            A context manager for the resource.

        """

        def _wrapper(func: typing.Callable[P, T]) -> typing.Callable[P, T]:
            if inspect.iscoroutinefunction(func):

                @wraps(func)
                async def _async_wrapper(*args: P.args, **kwargs: P.kwargs) -> T:
                    async with self.async_context(force=force):
                        return await func(*args, **kwargs)  # type: ignore[no-any-return, misc]

                return typing.cast(typing.Callable[P, T], _async_wrapper)

            # wrapped function is sync
            @wraps(func)
            def _sync_wrapper(*args: P.args, **kwargs: P.kwargs) -> T:
                with self.sync_context(force=force):
                    return func(*args, **kwargs)

            return typing.cast(typing.Callable[P, T], _sync_wrapper)

        if func:
            return _wrapper(func)
        return _wrapper

    def with_config(self, scope: ContextScope | None, strict_scope: bool = False) -> "ContextResource[T_co]":
        """Create a new context-resource with the specified scope.

        Args:
            scope: named scope where resource is resolvable.
            strict_scope: if True, the resource will only be resolvable in the specified scope.

        Returns:
            new context resource with the specified scope.

        """
        if strict_scope and scope == ContextScopes.ANY:
            msg = f"Cannot set strict_scope with scope {scope}."
            raise ValueError(msg)
        r = ContextResource(self._from_creator, *self._args, **self._kwargs)
        r._scope = scope  # noqa: SLF001
        r._strict_scope = strict_scope  # noqa: SLF001

        return r

    @override
    def supports_sync_context(self) -> bool:
        return not self.is_async

    def _enter_sync_context(self, force: bool = False) -> ResourceContext[T_co]:
        if self.is_async:
            msg = "You must enter async context for async creators."
            raise RuntimeError(msg)
        return self._enter(force)

    async def _enter_async_context(self, force: bool = False) -> ResourceContext[T_co]:
        return self._enter(force)

    def _enter(self, force: bool = False) -> ResourceContext[T_co]:
        if not force and self._scope not in (ContextScopes.ANY, get_current_scope()):
            msg = f"Cannot enter context for resource with scope {self._scope} in scope {get_current_scope()!r}"
            raise InvalidContextError(msg)
        self._token = self._context.set(ResourceContext(is_async=self.is_async))
        return self._context.get()

    def _exit_sync_context(self) -> None:
        if not self._token:
            msg = "Context is not set, call ``_enter_sync_context`` first"
            raise RuntimeError(msg)

        try:
            context_item = self._context.get()
            context_item.sync_tear_down()
        finally:
            self._context.reset(self._token)

    async def _exit_async_context(self) -> None:
        if self._token is None:
            msg = "Context is not set, call ``_enter_async_context`` first"
            raise RuntimeError(msg)

        try:
            context_item = self._context.get()
            if context_item.is_context_stack_async(context_item.context_stack):
                await context_item.tear_down()
            else:
                context_item.sync_tear_down()
        finally:
            self._context.reset(self._token)

    @contextlib.contextmanager
    @override
    def sync_context(self, force: bool = False) -> typing.Iterator[ResourceContext[T_co]]:
        if self.is_async:
            msg = "Please use async context instead."
            raise RuntimeError(msg)
        token = self._token
        with self._lock:
            val = self._enter_sync_context(force=force)
            temp_token = self._token
        yield val
        with self._lock:
            self._token = temp_token
            self._exit_sync_context()
        self._token = token

    @contextlib.asynccontextmanager
    @override
    async def async_context(self, force: bool = False) -> typing.AsyncIterator[ResourceContext[T_co]]:
        token = self._token

        async with self._async_lock:
            val = await self._enter_async_context(force=force)
            temp_token = self._token
        yield val
        async with self._async_lock:
            self._token = temp_token
            await self._exit_async_context()
        self._token = token

    def _fetch_context(self) -> ResourceContext[T_co]:
        try:
            return self._context.get()
        except LookupError as e:
            msg = "Context is not set. Use container_context"
            raise RuntimeError(msg) from e


ContainerType = typing.TypeVar("ContainerType", bound="type[BaseContainer]")


class container_context(AbstractContextManager[ContextType], AbstractAsyncContextManager[ContextType]):  # noqa: N801
    """Initialize contexts for the provided containers or resources.

    Use this class to manage global and resource-specific contexts in both
    synchronous and asynchronous scenarios.
    """

    ___slots__ = (
        "_providers",
        "_context_stack",
        "_containers",
        "_initial_context",
        "_context_token",
        "_reset_resource_context",
        "_scope",
    )

    def __init__(
        self,
        *context_items: SupportsContext[typing.Any],
        global_context: ContextType | None = None,
        preserve_global_context: bool = False,
        reset_all_containers: bool = False,
        scope: ContextScope | None = None,
    ) -> None:
        """Initialize a new container context.

        Args:
            *context_items (SupportsContext[Any]): Context items to initialize a new context for.
            global_context (dict[str, Any] | None): A dictionary representing the global context.
            preserve_global_context (bool): If True, merges the existing global context with the new one.
            reset_all_containers (bool): If True, creates a new context for all containers in this scope.
            scope (ContextScope | None): The named scope that should be initialized.

        Example:
            ```python
            async with container_context(MyContainer, global_context={"key": "value"}):
                data = fetch_context_item("key")
            ```

        """
        if scope == ContextScopes.ANY:
            msg = f"{scope} cannot be entered!"
            raise ValueError(msg)
        self._scope = scope
        self._preserve_global_context = preserve_global_context
        self._global_context = global_context
        self._context_token: Token[ContextType] | None = None
        self._context_items: set[SupportsContext[typing.Any]] = set(context_items)
        self._reset_resource_context: typing.Final[bool] = (
            not context_items and not global_context
        ) or reset_all_containers
        self._context_stack: contextlib.AsyncExitStack | contextlib.ExitStack | None = None
        self._scope_token: Token[ContextScope | None] | None = None

    def _resolve_initial_conditions(self) -> None:
        self._scope = self._scope if self._scope else get_current_scope()
        if self._preserve_global_context and self._global_context:
            self._initial_context = {**_get_container_context(), **self._global_context}
        else:
            self._initial_context: ContextType = (  # type: ignore[no-redef]
                _get_container_context() if self._preserve_global_context else self._global_context or {}
            )
        if self._reset_resource_context:  # equivalent to reset_all_containers
            self._add_providers_from_containers(BaseContainerMeta.get_instances(), self._scope)

    def _add_providers_from_containers(
        self, containers: list[ContainerType], scope: ContextScope | None = ContextScopes.ANY
    ) -> None:
        for container in containers:
            for container_provider in container.get_providers().values():
                if isinstance(container_provider, ContextResource):
                    provider_scope = container_provider.get_scope()
                    if provider_scope in (scope, ContextScopes.ANY):
                        self._context_items.add(container_provider)

    @override
    def __enter__(self) -> ContextType:
        self._resolve_initial_conditions()
        self._context_stack = contextlib.ExitStack()
        self._scope_token = _set_current_scope(self._scope)
        for item in self._context_items:
            if item.supports_sync_context():
                self._context_stack.enter_context(item.sync_context())
        return self._enter_globals()

    @override
    async def __aenter__(self) -> ContextType:
        self._resolve_initial_conditions()
        self._context_stack = contextlib.AsyncExitStack()
        self._scope_token = _set_current_scope(self._scope)
        for item in self._context_items:
            await self._context_stack.enter_async_context(item.async_context())
        return self._enter_globals()

    def _enter_globals(self) -> ContextType:
        self._context_token = _CONTAINER_CONTEXT.set(self._initial_context)
        return _CONTAINER_CONTEXT.get()

    def _is_context_token(self, _: Token[ContextType] | None) -> TypeIs[Token[ContextType]]:
        return _ is not None

    def _is_scope_token(self, _: Token[ContextScope | None] | None) -> TypeIs[Token[ContextScope | None]]:
        return _ is not None

    def _exit_globals(self) -> None:
        if self._is_context_token(self._context_token):
            _CONTAINER_CONTEXT.reset(self._context_token)
        else:
            msg = "No context token set for global vars, use __enter__ or __aenter__ first."
            raise RuntimeError(msg)
        if self._is_scope_token(self._scope_token):
            _CONTAINER_SCOPE.reset(self._scope_token)

    def _has_async_exit_stack(
        self,
        _: contextlib.AsyncExitStack | contextlib.ExitStack | None,
    ) -> typing.TypeGuard[contextlib.AsyncExitStack]:
        return isinstance(_, contextlib.AsyncExitStack)

    def _has_sync_exit_stack(
        self, _: contextlib.AsyncExitStack | contextlib.ExitStack | None
    ) -> typing.TypeGuard[contextlib.ExitStack]:
        return isinstance(_, contextlib.ExitStack)

    @override
    def __exit__(
        self, exc_type: type[BaseException] | None, exc_value: BaseException | None, traceback: TracebackType | None
    ) -> None:
        try:
            if self._has_sync_exit_stack(self._context_stack):
                self._context_stack.close()
            else:
                msg = "Context is not set, call ``__enter__`` first"
                raise RuntimeError(msg)
        finally:
            self._exit_globals()

    @override
    async def __aexit__(
        self, exc_type: type[BaseException] | None, exc_val: BaseException | None, traceback: TracebackType | None
    ) -> None:
        try:
            if self._has_async_exit_stack(self._context_stack):
                await self._context_stack.aclose()
            else:
                msg = "Context is not set, call ``__aenter__`` first"
                raise RuntimeError(msg)
        finally:
            self._exit_globals()

    def __call__(self, func: typing.Callable[P, T_co]) -> typing.Callable[P, T_co]:
        """Decorate a function to run within this container context.

        The context is automatically initialized before the function is called and
        torn down afterward.

        Args:
            func (Callable[P, T_co]): A sync or async callable.

        Returns:
            Callable[P, T_co]: The wrapped function.

        Example:
            ```python
            @container_context(MyContainer)
            async def my_async_function():
                result = await MyContainer.some_resource.async_resolve()
                return result
            ```

        """
        if inspect.iscoroutinefunction(func):

            @wraps(func)
            async def _async_inner(*args: P.args, **kwargs: P.kwargs) -> T_co:
                async with container_context(*self._context_items, reset_all_containers=self._reset_resource_context):
                    return await func(*args, **kwargs)  # type: ignore[no-any-return]

            return typing.cast(typing.Callable[P, T_co], _async_inner)

        @wraps(func)
        def _sync_inner(*args: P.args, **kwargs: P.kwargs) -> T_co:
            with container_context(*self._context_items, reset_all_containers=self._reset_resource_context):
                return func(*args, **kwargs)

        return _sync_inner


class DIContextMiddleware:
    """ASGI middleware that manages context initialization for incoming requests.

    This middleware automatically creates and tears down context for each request,
    ensuring that resources defined in containers or as context items are properly
    initialized and cleaned up.
    """

    def __init__(
        self,
        app: ASGIApp,
        *context_items: SupportsContext[typing.Any],
        global_context: dict[str, typing.Any] | None = None,
        reset_all_containers: bool = False,
        scope: ContextScope | None = None,
    ) -> None:
        """Initialize the DIContextMiddleware.

        Args:
            app (ASGIApp): The ASGI application to wrap.
            *context_items (SupportsContext[Any]): A collection of containers and providers that
                need context initialization prior to a request.
            global_context (dict[str, Any] | None): A global context dictionary to set before requests.
            reset_all_containers (bool): Whether to reset all containers in the current scope before the request.
            scope (ContextScope | None): The scope in which the context should be initialized.

        Example:
            ```python
            my_app.add_middleware(DIContextMiddleware, MyContainer, global_context={"api_key": "secret"})
            ```

        """
        self.app: typing.Final = app
        self._context_items: set[SupportsContext[typing.Any]] = set(context_items)
        self._global_context: dict[str, typing.Any] | None = global_context
        self._reset_all_containers: bool = reset_all_containers
        if scope == ContextScopes.ANY:
            msg = f"{scope} cannot be entered!"
            raise ValueError(msg)
        self._scope = scope

    async def __call__(self, scope: Scope, receive: Receive, send: Send) -> None:
        """Handle the incoming ASGI request by initializing and tearing down context.

        The context is initialized before the request is processed and
        closed after the request is completed.

        Args:
            scope (ContextScope): The ASGI scope.
            receive (Receive): The receive call.
            send (Send): The send call.

        Returns:
            None

        """
        async with (
            container_context(*self._context_items, global_context=self._global_context, scope=self._scope)
            if self._context_items
            else container_context(
                global_context=self._global_context, reset_all_containers=self._reset_all_containers, scope=self._scope
            )
        ):
            return await self.app(scope, receive, send)
