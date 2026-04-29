import asyncio
import contextlib
import inspect
import logging
import typing
from collections.abc import Iterable
from contextlib import AbstractAsyncContextManager, AbstractContextManager
from contextvars import ContextVar, Token
from functools import wraps
from types import TracebackType
from typing import Final, overload

from typing_extensions import Protocol, TypeIs, override, runtime_checkable

from that_depends.entities.resource_context import ResourceContext
from that_depends.providers.base import AbstractResource
from that_depends.utils import UNSET


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


class _SyncInjectionExitState(typing.Generic[T_co]):
    __slots__ = ("_context", "_context_item", "_token")

    def __init__(
        self,
        context: ContextVar[ResourceContext[T_co]],
        context_item: ResourceContext[T_co],
        token: Token[ResourceContext[T_co]],
    ) -> None:
        self._context = context
        self._context_item = context_item
        self._token = token

    def close(self) -> None:
        context_stack = self._context_item.context_stack
        if self._context_item.is_context_stack_sync(context_stack):
            context_stack.close()  # type: ignore[union-attr]
            self._context_item.context_stack = UNSET
            self._context_item.instance = UNSET
        self._context.reset(self._token)


class _SyncContextResourceContext(contextlib.ContextDecorator, AbstractContextManager[ResourceContext[T_co]]):
    __slots__ = ("_exit_state", "_force", "_provider")

    def __init__(self, provider: "ContextResource[T_co]", force: bool) -> None:
        self._provider = provider
        self._force = force
        self._exit_state: _SyncInjectionExitState[T_co] | None = None

    @override
    def __enter__(self) -> ResourceContext[T_co]:
        value, self._exit_state = self._provider._enter_injection_context_sync(force=self._force)  # noqa: SLF001
        return value

    @override
    def __exit__(
        self,
        exc_type: type[BaseException] | None,
        exc_value: BaseException | None,
        traceback: TracebackType | None,
    ) -> None:
        if self._exit_state is None:
            msg = "Context is not set, call ``__enter__`` first"
            raise RuntimeError(msg)
        _ = exc_type, exc_value, traceback
        self._exit_state.close()


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
    def __hash__(self) -> int:
        return hash(self.name)

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


@contextlib.contextmanager
def _enter_named_scope(scope: ContextScope) -> typing.Iterator[ContextScope]:
    token = _set_current_scope(scope)
    yield scope
    _CONTAINER_SCOPE.reset(token)


T = typing.TypeVar("T")
CT_co = typing.TypeVar("CT_co", covariant=True)


@runtime_checkable
class SupportsContext(Protocol[CT_co]):
    """Interface for resources that support context initialization.

    This interface defines methods to create synchronous and asynchronous
    context managers, as well as a function decorator for context initialization.
    """

    def get_scope(self) -> ContextScope | None:
        """Return the scope of the resource."""

    def context_async(self, force: bool = False) -> typing.AsyncContextManager[CT_co]:
        """Create an async context manager for this resource.

        Args:
            force (bool): If True, the context will be entered regardless of the current scope.

        Returns:
            AsyncContextManager[CT]: An async context manager.

        Example:
            ```python
            async with my_resource.context_async():
                result = await my_resource.resolve()
            ```

        """
        ...

    def context_sync(self, force: bool = False) -> typing.ContextManager[CT_co]:
        """Create a sync context manager for this resource.

        Args:
            force (bool): If True, the context will be entered regardless of the current scope.

        Returns:
            ContextManager[CT]: A sync context manager.

        Example:
            ```python
            with my_resource.context_sync():
                result = my_resource.resolve_sync()
            ```

        """
        ...

    def supports_context_sync(self) -> bool:
        """Check whether the resource supports sync context.

        Returns:
            bool: True if sync context is supported, False otherwise.

        """
        ...


BaseContainerType: typing.TypeAlias = type["BaseContainer"]


def _get_container_context() -> dict[str, typing.Any] | None:
    try:
        return _CONTAINER_CONTEXT.get()
    except LookupError:
        return None


def fetch_context_item(key: str, default: typing.Any = None, raise_on_not_found: bool = False) -> typing.Any:  # noqa: ANN401
    """Retrieve a value from the global context.

    Args:
        key (str): The key to retrieve from the global context.
        default (Any): The default value to return if the key is not found.
        raise_on_not_found (bool): If True, raises a KeyError if the key is not found.

    Returns:
        Any: The value associated with the key in the global context or the default value.

    Example:
        ```python
        async with container_context(global_context={"username": "john_doe"}):
            user = fetch_context_item("username")
        ```

    """
    if context := _get_container_context():
        return context.get(key, default)
    if raise_on_not_found:
        msg = f"Key `{key}` not found in global context."
        raise KeyError(msg)
    return default


def fetch_context_item_by_type(t: type[T]) -> T | None:
    """Retrieve a value from the global context by type.

    Args:
        t (type[T]): The type of the value to retrieve.

    Returns:
        T | None: The value associated with the type in the global context or None if not found.

    Raises:
        RuntimeError: If the context item of the specified type is not found in the global context.

    """
    if context := _get_container_context():
        for value in context.values():
            if isinstance(value, t):
                return value
    msg = f"Cannot find context item of type {t} in the global context."
    raise RuntimeError(msg)


class ContextResource(
    AbstractResource[T_co],
    SupportsContext[ResourceContext[T_co]],
):
    """A context-dependent provider that resolves resources only if their context is initialized.

    `ContextResource` handles both synchronous and asynchronous resource creators
    and ensures they are properly torn down when the context exits.
    """

    @override
    async def resolve(self) -> T_co:
        if not self._strict_scope or self._scope == ContextScopes.ANY:
            return await super().resolve()
        current_scope = get_current_scope()
        if self._scope == current_scope:
            return await super().resolve()
        msg = f"Cannot resolve resource with scope `{self._scope}` in scope `{current_scope}`"
        raise RuntimeError(msg)

    @override
    def resolve_sync(self) -> T_co:
        if not self._strict_scope or self._scope == ContextScopes.ANY:
            return super().resolve_sync()
        current_scope = get_current_scope()
        if self._scope == current_scope:
            return super().resolve_sync()
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
        "_is_async",
        "_kwargs",
        "_override",
        "_scope",
        "_token",
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
        self._from_creator: typing.Callable[..., typing.Iterator[T_co] | typing.AsyncIterator[T_co]] = creator
        self._is_context_resource = True
        self._context: ContextVar[ResourceContext[T_co]] = ContextVar(f"{self._creator.__name__}-context")
        self._token: Token[ResourceContext[T_co]] | None = None
        self._async_lock: Final = asyncio.Lock()
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
                    async with self.context_async(force=force):
                        return await func(*args, **kwargs)  # type: ignore[no-any-return]

                return typing.cast(typing.Callable[P, T], _async_wrapper)

            # wrapped function is sync
            @wraps(func)
            def _sync_wrapper(*args: P.args, **kwargs: P.kwargs) -> T:
                with self.context_sync(force=force):
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
        r._scope = scope
        r._strict_scope = strict_scope

        return r

    @override
    def supports_context_sync(self) -> bool:
        return not self._is_async

    def _enter_context_sync(self, force: bool = False) -> ResourceContext[T_co]:
        if self._is_async:
            msg = "You must enter async context for async creators."
            raise RuntimeError(msg)
        return self._enter(force)

    def _enter_injection_context_sync(
        self,
        force: bool = False,
    ) -> tuple[ResourceContext[T_co], _SyncInjectionExitState[T_co]]:
        if self._is_async:
            msg = "Please use async context instead."
            raise RuntimeError(msg)
        if not force and self._scope != ContextScopes.ANY:
            current_scope = get_current_scope()
            if self._scope != current_scope:
                msg = f"Cannot enter context for resource with scope {self._scope} in scope {current_scope!r}"
                raise InvalidContextError(msg)

        context_item: ResourceContext[T_co] = ResourceContext(is_async=False)
        token = self._context.set(context_item)
        return context_item, _SyncInjectionExitState(self._context, context_item, token)

    async def _enter_context_async(self, force: bool = False) -> ResourceContext[T_co]:
        return self._enter(force)

    def _enter(self, force: bool = False) -> ResourceContext[T_co]:
        if not force and self._scope != ContextScopes.ANY:
            current_scope = get_current_scope()
            if self._scope != current_scope:
                msg = f"Cannot enter context for resource with scope {self._scope} in scope {current_scope!r}"
                raise InvalidContextError(msg)
        context_item: ResourceContext[T_co] = ResourceContext(is_async=self._is_async)
        self._token = self._context.set(context_item)
        return context_item

    def _exit_context_sync(self) -> None:
        if self._token is None:
            msg = "Context is not set, call ``_enter_sync_context`` first"
            raise RuntimeError(msg)

        try:
            context_item = self._context.get()
            context_stack = context_item.context_stack
            if context_item.is_context_stack_sync(context_stack):
                context_stack.close()  # type: ignore[union-attr]
                context_item.context_stack = UNSET
                context_item.instance = UNSET
        finally:
            self._context.reset(self._token)

    async def _exit_context_async(self) -> None:
        if self._token is None:
            msg = "Context is not set, call ``_enter_async_context`` first"
            raise RuntimeError(msg)

        try:
            context_item = self._context.get()
            if context_item.is_context_stack_async(context_item.context_stack):
                await context_item.tear_down()
            else:
                context_item.tear_down_sync()
        finally:
            self._context.reset(self._token)

    @override
    def context_sync(self, force: bool = False) -> _SyncContextResourceContext[T_co]:
        return _SyncContextResourceContext(self, force)

    @contextlib.asynccontextmanager
    @override
    async def context_async(self, force: bool = False) -> typing.AsyncIterator[ResourceContext[T_co]]:
        token = self._token

        async with self._async_lock:
            val = await self._enter_context_async(force=force)
            temp_token = self._token
        yield val
        async with self._async_lock:
            self._token = temp_token
            await self._exit_context_async()
        self._token = token

    def _fetch_context(self) -> ResourceContext[T_co]:
        try:
            return self._context.get()
        except LookupError as e:
            msg = "Context is not set. Use container_context"
            raise RuntimeError(msg) from e


class container_context(AbstractContextManager[ContextType], AbstractAsyncContextManager[ContextType]):  # noqa: N801
    """Initialize contexts for the provided containers or resources.

    Use this class to manage global and resource-specific contexts in both
    synchronous and asynchronous scenarios.
    """

    __slots__ = (
        "_container_items",
        "_container_providers_by_scope",
        "_context_items",
        "_context_stack",
        "_context_token",
        "_direct_context_items",
        "_entered_context_items",
        "_global_context",
        "_initial_context",
        "_preserve_global_context",
        "_reset_resource_context",
        "_scope",
        "_scope_token",
    )

    def __init__(
        self,
        *context_items: SupportsContext[typing.Any],
        global_context: ContextType | None = None,
        preserve_global_context: bool = True,
        scope: ContextScope | None = None,
    ) -> None:
        """Initialize a new container context.

        Args:
            *context_items: Context-capable providers or container classes to initialize.
            global_context (dict[str, Any] | None): A dictionary representing the global context.
            preserve_global_context (bool): If True, merges the existing global context with the new one.
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
        if len(context_items) == 0 and not scope and not global_context:
            msg = "One of context_items, scope or global_context must be provided."
            raise ValueError(msg)
        self._scope = scope
        self._preserve_global_context = preserve_global_context
        self._global_context = global_context
        self._context_token: Token[ContextType] | None = None
        self._context_items: typing.Final[set[SupportsContext[typing.Any]]] = set(context_items)
        self._container_items: tuple[type[BaseContainer], ...]
        self._direct_context_items: tuple[SupportsContext[typing.Any], ...]
        self._container_providers_by_scope: dict[ContextScope | None, tuple[ContextResource[typing.Any], ...]] = {}
        self._entered_context_items: tuple[SupportsContext[typing.Any], ...] = ()
        self._reset_resource_context: typing.Final[bool] = bool(scope)
        self._context_stack: contextlib.AsyncExitStack | contextlib.ExitStack | None = None
        self._scope_token: Token[ContextScope | None] | None = None
        self._container_items, self._direct_context_items = self._parse_context_items(self._context_items)

    def _parse_context_items(
        self,
        context_items: set[SupportsContext[typing.Any]],
    ) -> tuple[tuple[type["BaseContainer"], ...], tuple[SupportsContext[typing.Any], ...]]:
        from that_depends.container import BaseContainer  # noqa: PLC0415

        containers: list[type[BaseContainer]] = []
        direct_items: list[SupportsContext[typing.Any]] = []
        for item in context_items:
            if isinstance(item, type) and issubclass(item, BaseContainer):
                containers.append(item)
            else:
                direct_items.append(item)
        return tuple(containers), tuple(direct_items)

    def _get_context_providers_for_scope(
        self,
        scope: ContextScope | None,
    ) -> tuple[ContextResource[typing.Any], ...]:
        cached = self._container_providers_by_scope.get(scope)
        if cached is None:
            providers: set[ContextResource[typing.Any]] = set()
            self._add_providers_from_containers(self._container_items, providers, scope)
            cached = tuple(providers)
            self._container_providers_by_scope[scope] = cached
        return cached

    def _resolve_initial_conditions(self) -> ContextScope | None:
        scope = self._scope or get_current_scope()
        if self._preserve_global_context and self._global_context:
            if context := _get_container_context():
                self._initial_context = {**context, **self._global_context}
            else:
                self._initial_context = self._global_context
        elif context := _get_container_context():
            self._initial_context: ContextType = (  # type: ignore[no-redef]
                context if self._preserve_global_context else self._global_context or {}
            )
        else:
            self._initial_context = self._global_context or {}
        entered_context_items = dict.fromkeys(self._direct_context_items)
        for provider in self._get_context_providers_for_scope(scope):
            entered_context_items[provider] = provider
        if self._reset_resource_context:
            from that_depends.meta import BaseContainerMeta  # noqa: PLC0415

            scope_providers: set[ContextResource[typing.Any]] = set()
            self._add_providers_from_containers(BaseContainerMeta.get_instances().values(), scope_providers, scope)
            for provider in scope_providers:
                entered_context_items[provider] = provider
        self._entered_context_items = tuple(entered_context_items)
        return scope

    def _add_providers_from_containers(
        self,
        containers: Iterable[BaseContainerType],
        target: set[ContextResource[typing.Any]],
        scope: ContextScope | None = ContextScopes.ANY,
    ) -> None:
        for container in containers:
            for container_provider in container.get_providers().values():
                if isinstance(container_provider, ContextResource):
                    provider_scope = container_provider.get_scope()
                    if provider_scope in (scope, ContextScopes.ANY):
                        target.add(container_provider)

    @override
    def __enter__(self) -> ContextType:
        scope = self._resolve_initial_conditions()
        self._context_stack = contextlib.ExitStack()
        self._scope_token = _set_current_scope(scope)
        for item in self._entered_context_items:
            if item.supports_context_sync():
                self._context_stack.enter_context(item.context_sync())
        return self._enter_globals()

    @override
    async def __aenter__(self) -> ContextType:
        scope = self._resolve_initial_conditions()
        self._context_stack = contextlib.AsyncExitStack()
        self._scope_token = _set_current_scope(scope)
        for item in self._entered_context_items:
            await self._context_stack.enter_async_context(item.context_async())
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
                result = await MyContainer.some_resource.resolve()
                return result
            ```

        """
        if inspect.isasyncgenfunction(func) or inspect.isgeneratorfunction(func):
            msg = "@container_context cannot be used to wrap generators."
            raise UserWarning(msg)

        if inspect.iscoroutinefunction(func):

            @wraps(func)
            async def _async_inner(*args: P.args, **kwargs: P.kwargs) -> T_co:
                async with container_context(
                    *self._context_items,
                    scope=self._scope,
                    global_context=self._global_context,
                    preserve_global_context=self._preserve_global_context,
                ):
                    return await func(*args, **kwargs)  # type: ignore[no-any-return]

            return typing.cast(typing.Callable[P, T_co], _async_inner)

        @wraps(func)
        def _sync_inner(*args: P.args, **kwargs: P.kwargs) -> T_co:
            with container_context(
                *self._context_items,
                scope=self._scope,
                global_context=self._global_context,
                preserve_global_context=self._preserve_global_context,
            ):
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
        scope: ContextScope | None = None,
    ) -> None:
        """Initialize the DIContextMiddleware.

        Args:
            app (ASGIApp): The ASGI application to wrap.
            *context_items: Containers and providers that need context initialization prior to a request.
            global_context (dict[str, Any] | None): A global context dictionary to set before requests.
            scope (ContextScope | None): The scope in which the context should be initialized.

        Example:
            ```python
            my_app.add_middleware(DIContextMiddleware, MyContainer, global_context={"api_key": "secret"})
            ```

        """
        self.app: typing.Final = app
        self._context_items: set[SupportsContext[typing.Any]] = set(context_items)
        self._global_context: dict[str, typing.Any] | None = global_context
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
            else container_context(global_context=self._global_context, scope=self._scope)
        ):
            return await self.app(scope, receive, send)
