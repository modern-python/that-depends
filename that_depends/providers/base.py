import abc
import contextlib
import inspect
import threading
import typing
from contextlib import asynccontextmanager, contextmanager
from operator import attrgetter

import typing_extensions
from typing_extensions import override

from that_depends.entities.resource_context import ResourceContext
from that_depends.providers.mixin import ProviderWithArguments, SupportsTeardown


T_co = typing.TypeVar("T_co", covariant=True)
R = typing.TypeVar("R")
P = typing.ParamSpec("P")
ResourceCreatorType: typing.TypeAlias = typing.Callable[
    P,
    typing.Iterator[T_co]
    | typing.AsyncIterator[T_co]
    | contextlib.AbstractContextManager[T_co]
    | contextlib.AbstractAsyncContextManager[T_co],
]
_EMPTY_ARGS: typing.Final[tuple[()]] = ()
_EMPTY_KWARGS: typing.Final[dict[str, typing.Any]] = {}


async def _resolve_arguments(
    args: tuple[typing.Any, ...],
    args_are_providers: tuple[bool, ...],
) -> tuple[typing.Any, ...] | list[typing.Any]:
    if not args:
        return _EMPTY_ARGS
    if len(args) == 1:
        arg = args[0]
        return (await arg.resolve() if args_are_providers[0] else arg,)
    return [
        await arg.resolve() if is_provider else arg for arg, is_provider in zip(args, args_are_providers, strict=False)
    ]


def _resolve_arguments_sync(
    args: tuple[typing.Any, ...],
    args_are_providers: tuple[bool, ...],
) -> tuple[typing.Any, ...] | list[typing.Any]:
    if not args:
        return _EMPTY_ARGS
    if len(args) == 1:
        arg = args[0]
        return (arg.resolve_sync() if args_are_providers[0] else arg,)
    return [
        arg.resolve_sync() if is_provider else arg for arg, is_provider in zip(args, args_are_providers, strict=False)
    ]


async def _resolve_keyword_arguments(
    kwargs_items: tuple[tuple[str, typing.Any], ...],
    kwargs_are_providers: tuple[bool, ...],
) -> dict[str, typing.Any]:
    if not kwargs_items:
        return _EMPTY_KWARGS
    if len(kwargs_items) == 1:
        key, value = kwargs_items[0]
        return {key: await value.resolve() if kwargs_are_providers[0] else value}
    return {
        key: await value.resolve() if is_provider else value
        for (key, value), is_provider in zip(kwargs_items, kwargs_are_providers, strict=False)
    }


def _resolve_keyword_arguments_sync(
    kwargs_items: tuple[tuple[str, typing.Any], ...],
    kwargs_are_providers: tuple[bool, ...],
) -> dict[str, typing.Any]:
    if not kwargs_items:
        return _EMPTY_KWARGS
    if len(kwargs_items) == 1:
        key, value = kwargs_items[0]
        return {key: value.resolve_sync() if kwargs_are_providers[0] else value}
    return {
        key: value.resolve_sync() if is_provider else value
        for (key, value), is_provider in zip(kwargs_items, kwargs_are_providers, strict=False)
    }


class AbstractProvider(abc.ABC, typing.Generic[T_co]):
    """Base class for all providers."""

    def __init__(self) -> None:
        """Create a new provider."""
        super().__init__()
        self._children: set[AbstractProvider[typing.Any]] = set()
        self._parents: set[AbstractProvider[typing.Any]] = set()
        self._is_context_resource = False
        self._scope_context_init_order: tuple[AbstractProvider[typing.Any], ...] | None = None
        self._scope_init_order: tuple[AbstractProvider[typing.Any], ...] | None = None
        self._override: typing.Any = None
        self._bindings: set[type] = set()
        self._has_contravariant_bindings: bool = False
        self._lock = threading.Lock()

    def bind(self, *types: type, contravariant: bool = False) -> typing_extensions.Self:
        """Bind the provider to a set of types.

        Calling this method multiple times will overwrite the previous bindings.

        Args:
            *types (type): types the provider can provide.
            contravariant: whether provider can provider contravariant types.

        Returns:
            The current provider instance.

        """
        self._bindings = set(types)
        self._has_contravariant_bindings = contravariant
        return self

    def _register(self, candidates: typing.Iterable[typing.Any]) -> None:
        """Register current provider as child.

        Args:
            candidates: iterable of potential parent providers.

        Returns:
            None

        """
        changed = False
        for candidate in candidates:
            if isinstance(candidate, AbstractProvider):
                candidate.add_child_provider(self)
                self._parents.add(candidate)
                changed = True
        if changed:
            self._invalidate_scope_init_order()

    def _deregister(self, candidates: typing.Iterable[typing.Any]) -> None:
        """Deregister current provider as child.

        Args:
            candidates: iterable of potential parent providers.

        Returns:
            None

        """
        changed = False
        for candidate in candidates:
            if isinstance(candidate, AbstractProvider) and self in candidate._children:  # noqa: SLF001
                candidate.remove_child_provider(self)
                self._parents.discard(candidate)
                changed = True
        if changed:
            self._invalidate_scope_init_order()

    def _invalidate_scope_init_order(self) -> None:
        stack = [self]
        visited: set[AbstractProvider[typing.Any]] = set()

        while stack:
            provider = stack.pop()
            if provider in visited:
                continue
            visited.add(provider)
            provider._scope_context_init_order = None  # noqa: SLF001
            provider._scope_init_order = None  # noqa: SLF001
            stack.extend(provider._children)  # noqa: SLF001

    def _get_scope_init_order(self) -> tuple["AbstractProvider[typing.Any]", ...]:
        if self._scope_init_order is not None:
            return self._scope_init_order

        if isinstance(self, ProviderWithArguments):
            self._register_arguments()

        ordered: list[AbstractProvider[typing.Any]] = []
        seen: set[AbstractProvider[typing.Any]] = set()

        for parent in self._parents:
            for ancestor in parent._get_scope_init_order():  # noqa: SLF001
                if ancestor not in seen:
                    seen.add(ancestor)
                    ordered.append(ancestor)

        if self not in seen:
            ordered.append(self)

        self._scope_init_order = tuple(ordered)
        return self._scope_init_order

    def _get_scope_context_init_order(self) -> tuple["AbstractProvider[typing.Any]", ...]:
        if self._scope_context_init_order is not None:
            return self._scope_context_init_order

        if isinstance(self, ProviderWithArguments):
            self._register_arguments()

        ordered: list[AbstractProvider[typing.Any]] = []
        seen: set[AbstractProvider[typing.Any]] = set()

        for parent in self._parents:
            for ancestor in parent._get_scope_context_init_order():  # noqa: SLF001
                if ancestor not in seen:
                    seen.add(ancestor)
                    ordered.append(ancestor)

        if self._is_context_resource and self not in seen:
            ordered.append(self)

        self._scope_context_init_order = tuple(ordered)
        return self._scope_context_init_order

    def add_child_provider(self, provider: "AbstractProvider[typing.Any]") -> None:
        """Add a child provider to the current provider.

        Args:
            provider: provider to add as a child.

        Returns:
            None

        """
        with self._lock:
            self._children.add(provider)

    def remove_child_provider(self, provider: "AbstractProvider[typing.Any]") -> None:
        """Remove a child provider from the current provider.

        Args:
            provider: provider to remove as a child.

        Returns:
            None

        """
        with self._lock:
            self._children.discard(provider)

    def __deepcopy__(self, *_: object, **__: object) -> typing_extensions.Self:
        """Hack for Litestar to prevent cloning object.

        More info here https://github.com/modern-python/that-depends/issues/119.
        """
        return self

    def __getattr__(self, attr_name: str) -> typing.Any:  # noqa: ANN401
        """Get an attribute from the resolve object.

        Args:
            attr_name: name of attribute to get.

        Returns:
            An `AttrGetter` provider that will get the attribute after resolving the current provider.

        """
        if attr_name.startswith("_"):
            msg = f"'{type(self)}' object has no attribute '{attr_name}'"
            raise AttributeError(msg)
        return AttrGetter(provider=self, attr_name=attr_name)

    @abc.abstractmethod
    async def resolve(self) -> T_co:
        """Resolve dependency asynchronously."""

    @abc.abstractmethod
    def resolve_sync(self) -> T_co:
        """Resolve dependency synchronously."""

    async def __call__(self) -> T_co:
        """Resolve dependency asynchronously."""
        return await self.resolve()

    def override_sync(
        self, mock: object, tear_down_children: bool = False, propagate: bool = True, raise_on_async: bool = False
    ) -> None:
        """Override the provider with a mock object.

        Args:
            mock: object to resolve while the provider is overridden.
            tear_down_children: tear down child providers.
            raise_on_async: raise if tear down requires async context.
            propagate: propagate teardown.

        Returns:
            None

        """
        self._override = mock
        if tear_down_children:
            eligible_children = [child for child in self._children if isinstance(child, SupportsTeardown)]
            for child in eligible_children:
                child.tear_down_sync(propagate=propagate, raise_on_async=raise_on_async)

    async def override(self, mock: object, tear_down_children: bool = False, propagate: bool = True) -> None:
        """Override the provider with a mock object.

        Args:
            mock: object to resolve while the provider is overridden.
            tear_down_children: tear down child providers.
            propagate: propagate teardown.

        Returns:
            None

        """
        self._override = mock
        if tear_down_children:
            eligible_children = [child for child in self._children if isinstance(child, SupportsTeardown)]
            for child in eligible_children:
                await child.tear_down(propagate=propagate)

    @contextmanager
    def override_context_sync(self, mock: object) -> typing.Iterator[None]:
        """Override the provider with a mock object temporarily.

        Args:
            mock: object to resolve while the provider is overridden.

        Returns:
            None

        """
        self.override_sync(mock)
        try:
            yield
        finally:
            self.reset_override_sync()

    @asynccontextmanager
    async def override_context(self, mock: object) -> typing.AsyncIterator[None]:
        """Override the provider with a mock object temporarily.

        Args:
            mock: object to resolve while the provider is overridden.

        Returns:
            None

        """
        await self.override(mock)
        try:
            yield
        finally:
            self.reset_override_sync()

    def reset_override_sync(
        self, tear_down_children: bool = False, propagate: bool = True, raise_on_async: bool = False
    ) -> None:
        """Reset the provider to its original state.

        Use this is you have previously called `override` or `override_context`
        to reset the provider to its original state.

        Args:
            tear_down_children: tear down all child providers.
            raise_on_async: raise if an async teardown is necessary.
            propagate: propagate tear downs.

        Returns:
            None

        """
        self._override = None
        if tear_down_children:
            eligible_children = [child for child in self._children if isinstance(child, SupportsTeardown)]
            for child in eligible_children:
                child.tear_down_sync(propagate=propagate, raise_on_async=raise_on_async)

    async def reset_override(self, tear_down_children: bool = False, propagate: bool = True) -> None:
        """Reset the provider to its original state.

        Args:
            tear_down_children: tear down all child providers.
            propagate: propagate tear downs.

        Returns:
            None

        """
        self._override = None
        if tear_down_children:
            eligible_children = [child for child in self._children if isinstance(child, SupportsTeardown)]
            for child in eligible_children:
                await child.tear_down(propagate=propagate)

    @property
    def cast(self) -> T_co:
        """Returns self, but cast to the type of the provided value.

        This helps to pass providers as input to other providers while avoiding type checking errors:

        Example:
            class A: ...

            def create_b(a: A) -> B: ...

            class Container(BaseContainer):
                a_factory = Factory(A)
                b_factory1 = Factory(create_b, a_factory)  # works, but mypy (or pyright, etc.) will complain
                b_factory2 = Factory(create_b, a_factory.cast)  # works and passes type checking

        """
        return typing.cast(T_co, self)

    async def _tear_down_children(self) -> None:
        """Tear down all child providers."""
        eligible_children = [child for child in self._children if isinstance(child, SupportsTeardown)]
        for child in eligible_children:
            await child.tear_down()

    def _tear_down_children_sync(self, propagate: bool = True, raise_on_async: bool = True) -> None:
        """Tear down all child providers."""
        eligible_children = [child for child in self._children if isinstance(child, SupportsTeardown)]
        for child in eligible_children:
            child.tear_down_sync(raise_on_async=raise_on_async, propagate=propagate)


class AbstractResource(ProviderWithArguments, AbstractProvider[T_co], abc.ABC):
    """Base class for Resource providers."""

    def __init__(
        self,
        creator: ResourceCreatorType[P, T_co],
        *args: P.args,
        **kwargs: P.kwargs,
    ) -> None:
        """Create a new resource.

        Args:
            creator: sync or async iterator or context manager that yields resource.
            *args: positional arguments to pass to the creator.
            **kwargs: keyword arguments to pass to the creator.


        """
        super().__init__()
        self._creator: typing.Callable[
            ...,
            contextlib.AbstractContextManager[T_co] | contextlib.AbstractAsyncContextManager[T_co],
        ]

        if inspect.isasyncgenfunction(creator):
            self._is_async = True
            self._creator = contextlib.asynccontextmanager(creator)
        elif inspect.isgeneratorfunction(creator):
            self._is_async = False
            self._creator = contextlib.contextmanager(creator)
        elif isinstance(creator, type) and hasattr(creator, "__aenter__") and hasattr(creator, "__aexit__"):
            self._is_async = True
            self._creator = creator
        elif isinstance(creator, type) and hasattr(creator, "__enter__") and hasattr(creator, "__exit__"):
            self._is_async = False
            self._creator = creator
        else:
            msg = "Unsupported resource type"
            raise TypeError(msg)
        self._args = args
        self._kwargs = kwargs
        self._args_are_providers = tuple(isinstance(arg, AbstractProvider) for arg in args)
        self._kwargs_items = tuple(kwargs.items())
        self._kwargs_are_providers = tuple(isinstance(value, AbstractProvider) for _, value in self._kwargs_items)

    def _register_arguments(self) -> None:
        if not self._mark_arguments_registered():
            return
        self._register(self._args)
        self._register(self._kwargs.values())

    def _deregister_arguments(self) -> None:
        self._deregister(self._args)
        self._deregister(self._kwargs.values())
        self._reset_arguments_registration()

    @abc.abstractmethod
    def _fetch_context(self) -> ResourceContext[T_co]: ...

    @override
    async def resolve(self) -> T_co:
        if self._override:
            return typing.cast(T_co, self._override)

        context = self._fetch_context()

        # lock to prevent race condition while resolving
        async with context.asyncio_lock:
            if context.instance is not None:
                return context.instance

            self._register_arguments()
            cm: contextlib.AbstractContextManager[T_co] | contextlib.AbstractAsyncContextManager[T_co] = self._creator(
                *await _resolve_arguments(self._args, self._args_are_providers),
                **await _resolve_keyword_arguments(self._kwargs_items, self._kwargs_are_providers),
            )

            if isinstance(cm, contextlib.AbstractAsyncContextManager):
                context.context_stack = contextlib.AsyncExitStack()
                context.instance = await context.context_stack.enter_async_context(cm)

            elif isinstance(cm, contextlib.AbstractContextManager):
                context.context_stack = contextlib.ExitStack()
                context.instance = context.context_stack.enter_context(cm)

            else:  # pragma: no cover
                typing.assert_never(cm)

        return context.instance

    @override
    def resolve_sync(self) -> T_co:
        if self._override:
            return typing.cast(T_co, self._override)

        context = self._fetch_context()

        # lock to prevent race condition while resolving
        with context.threading_lock:
            if context.instance is not None:
                return context.instance

            if self._is_async:
                msg = "AsyncResource cannot be resolved synchronously"
                raise RuntimeError(msg)

            self._register_arguments()
            cm = self._creator(
                *_resolve_arguments_sync(self._args, self._args_are_providers),
                **_resolve_keyword_arguments_sync(self._kwargs_items, self._kwargs_are_providers),
            )
            context.context_stack = contextlib.ExitStack()
            instance: T_co = context.context_stack.enter_context(cm)  # type: ignore[arg-type]
            context.instance = instance

            return instance


def _get_value_from_object_by_dotted_path(obj: typing.Any, path: str) -> typing.Any:  # noqa: ANN401
    attribute_getter = attrgetter(path)
    return attribute_getter(obj)


class AttrGetter(
    ProviderWithArguments,
    AbstractProvider[T_co],
):
    """Provides an attribute after resolving the wrapped provider."""

    def _register_arguments(self) -> None:
        if not self._mark_arguments_registered():
            return
        if isinstance(self._provider, ProviderWithArguments):
            self._provider._register_arguments()  # noqa: SLF001
        self._parents = self._provider._parents  # noqa: SLF001

    def _deregister_arguments(self) -> None:
        if isinstance(self._provider, ProviderWithArguments):
            self._provider._deregister_arguments()  # noqa: SLF001
        self._parents = self._provider._parents  # noqa: SLF001
        self._reset_arguments_registration()

    __slots__ = "_attrs", "_provider"

    def __init__(self, provider: AbstractProvider[T_co], attr_name: str) -> None:
        """Create a new AttrGetter instance.

        Args:
            provider: provider to wrap.
            attr_name: attribute name to resolve when the provider is resolved.

        """
        super().__init__()
        self._provider = provider
        self._attrs = [attr_name]

    @override
    def __getattr__(self, attr_name: str) -> "AttrGetter[T_co]":
        if attr_name.startswith("_"):
            msg = f"'{type(self)}' object has no attribute '{attr_name}'"
            raise AttributeError(msg)
        self._attrs.append(attr_name)
        return self

    @override
    async def resolve(self) -> typing.Any:
        resolved_provider_object = await self._provider.resolve()
        attribute_path = ".".join(self._attrs)
        return _get_value_from_object_by_dotted_path(resolved_provider_object, attribute_path)

    @override
    def resolve_sync(self) -> typing.Any:
        resolved_provider_object = self._provider.resolve_sync()
        attribute_path = ".".join(self._attrs)
        return _get_value_from_object_by_dotted_path(resolved_provider_object, attribute_path)

    @override
    def add_child_provider(self, provider: "AbstractProvider[typing.Any]") -> None:
        self._provider.add_child_provider(provider)
