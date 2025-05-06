import asyncio
import contextlib
import functools
import inspect
import re
import threading
import typing
import warnings
from contextlib import AsyncExitStack, ExitStack

from that_depends.container import BaseContainer
from that_depends.exceptions import TypeNotBoundError
from that_depends.meta import BaseContainerMeta
from that_depends.providers import AbstractProvider, ContextResource
from that_depends.providers.context_resources import ContextScope, ContextScopes, container_context
from that_depends.providers.mixin import ProviderWithArguments


class ContextProviderError(Exception):
    """Exception raised when a context provider is used where it is not expected."""


P = typing.ParamSpec("P")
T = typing.TypeVar("T")
_STRING_PROVIDER_PATTERN = re.compile(r"^([^.]+)\.([^.]+)(?:\.(.+))?$")
_INJECTION_WARNING_MESSAGE: typing.Final[str] = "Expected injection, but nothing found. Remove @inject decorator."
_PROVIDE_MESSAGE: typing.Final[str] = (
    "Use @Container.inject or @inject(container=Container) if you wish to use Provide()"
)


@typing.overload
def inject(func: typing.Callable[P, T]) -> typing.Callable[P, T]: ...


@typing.overload
def inject(
    *,
    scope: ContextScope | None = ContextScopes.INJECT,
    container: BaseContainerMeta | None = None,
    enter_scope: bool = False,
) -> typing.Callable[[typing.Callable[P, T]], typing.Callable[P, T]]: ...


def inject(  # noqa: C901
    func: typing.Callable[P, T] | None = None,
    scope: ContextScope | None = ContextScopes.INJECT,
    container: BaseContainerMeta | None = None,
    enter_scope: bool = False,
) -> typing.Callable[P, T] | typing.Callable[[typing.Callable[P, T]], typing.Callable[P, T]]:
    """Mark a function for dependency injection.

    Args:
        func: function or generator function to be wrapped.
        scope: scope to initialize ContextResources for.
        container: container from which to resolve dependencies marked with `Provide()`.
        enter_scope: enter the provided scope.

    Returns:
        wrapped function.

    """
    if scope == ContextScopes.ANY:
        msg = f"{scope} is not allowed in inject decorator."
        raise ValueError(msg)
    if scope is None and enter_scope:
        msg = "enter_scope cannot be used with scope=None."
        raise ValueError(msg)

    def _inject(
        func: typing.Callable[P, T],
    ) -> typing.Callable[P, T]:
        if inspect.isasyncgenfunction(func):
            if enter_scope:
                msg = "enter_scope cannot be used with async generator functions."
                raise ValueError(msg)
            return typing.cast(typing.Callable[P, T], _inject_to_async_gen(func))
        if inspect.isgeneratorfunction(func):
            if enter_scope:
                msg = "enter_scope cannot be used with generator functions."
                raise ValueError(msg)
            return typing.cast(typing.Callable[P, T], _inject_to_sync_gen(func))
        if inspect.iscoroutinefunction(func):
            return typing.cast(typing.Callable[P, T], _inject_to_async(func))

        return _inject_to_sync(func)

    def _inject_to_sync_gen(
        gen: typing.Callable[P, typing.Generator[T, typing.Any, typing.Any]],
    ) -> typing.Callable[P, typing.Generator[T, typing.Any, typing.Any]]:
        @functools.wraps(gen)
        def inner(*args: P.args, **kwargs: P.kwargs) -> typing.Generator[T, typing.Any, typing.Any]:
            signature = inspect.signature(gen)
            injected, kwargs = _resolve_arguments_sync(signature, scope, container, None, *args, **kwargs)  # type: ignore[assignment]

            if not injected:
                warnings.warn(_INJECTION_WARNING_MESSAGE, RuntimeWarning, stacklevel=1)

            g = gen(*args, **kwargs)
            result = yield from g
            return result

        return inner

    def _inject_to_async_gen(
        gen: typing.Callable[P, typing.AsyncGenerator[T, typing.Any]],
    ) -> typing.Callable[P, typing.AsyncGenerator[T, typing.Any]]:
        @functools.wraps(gen)
        async def inner(*args: P.args, **kwargs: P.kwargs) -> typing.AsyncGenerator[T, typing.Any]:
            signature = inspect.signature(gen)

            injected, kwargs = await _resolve_arguments_async(signature, scope, container, None, *args, **kwargs)  # type: ignore[assignment]

            if not injected:
                warnings.warn(_INJECTION_WARNING_MESSAGE, RuntimeWarning, stacklevel=1)

            async for item in gen(*args, **kwargs):
                yield item

        return inner

    def _inject_to_async(
        func: typing.Callable[P, typing.Coroutine[typing.Any, typing.Any, T]],
    ) -> typing.Callable[P, typing.Coroutine[typing.Any, typing.Any, T]]:
        @functools.wraps(func)
        async def inner(*args: P.args, **kwargs: P.kwargs) -> T:
            if enter_scope:
                async with container_context(scope=scope):
                    return await _resolve_async(func, None, container, *args, **kwargs)
            else:
                return await _resolve_async(func, scope, container, *args, **kwargs)

        return inner

    def _inject_to_sync(
        func: typing.Callable[P, T],
    ) -> typing.Callable[P, T]:
        @functools.wraps(func)
        def inner(*args: P.args, **kwargs: P.kwargs) -> T:
            if enter_scope:
                with container_context(scope=scope):
                    return _resolve_sync(func, None, container, *args, **kwargs)
            else:
                return _resolve_sync(func, scope, container, *args, **kwargs)

        return inner

    if func is None:
        return _inject
    return _inject(func)


_SYNC_SIGNATURE_CACHE: dict[typing.Callable[..., typing.Any], inspect.Signature] = {}
_THREADING_LOCK = threading.Lock()


async def _resolve_arguments_async(
    signature: inspect.Signature,
    scope: ContextScope | None,
    container: BaseContainerMeta | None,
    stack: AsyncExitStack | None,
    *args: typing.Any,  # noqa: ANN401
    **kwargs: typing.Any,  # noqa: ANN401
) -> tuple[bool, dict[str, typing.Any]]:
    injected = False
    context_providers: set[AbstractProvider[typing.Any]] = set()
    params = list(signature.parameters.items())

    for i, (field_name, param) in enumerate(params):
        default = param.default

        if i < len(args) or field_name in kwargs:
            if isinstance(default, (AbstractProvider, StringProviderDefinition)):
                injected = True
            continue

        if isinstance(default, StringProviderDefinition):
            injected = True
            resolved_val = await _resolve_provider_with_scope_async(default.provider, scope, stack, context_providers)
            kwargs[field_name] = resolved_val
        elif isinstance(default, AbstractProvider):
            injected = True
            resolved_val = await _resolve_provider_with_scope_async(default, scope, stack, context_providers)
            kwargs[field_name] = resolved_val

        elif isinstance(default, _Provide):
            injected = True
            if container is None:
                raise RuntimeError(_PROVIDE_MESSAGE)
            try:
                provider = container.get_provider_for_type(signature.parameters[field_name].annotation)
            except TypeNotBoundError as e:
                msg = f"Type {signature.parameters[field_name].annotation} is not bound to a provider."
                raise RuntimeError(msg) from e
            kwargs[field_name] = await _resolve_provider_with_scope_async(provider, scope, stack, context_providers)
    return injected, kwargs


def _resolve_arguments_sync(
    signature: inspect.Signature,
    scope: ContextScope | None,
    container: BaseContainerMeta | None,
    stack: contextlib.ExitStack | None,
    *args: typing.Any,  # noqa: ANN401
    **kwargs: typing.Any,  # noqa: ANN401
) -> tuple[bool, dict[str, typing.Any]]:
    injected = False
    context_providers: set[AbstractProvider[typing.Any]] = set()
    for i, (field_name, param) in enumerate(signature.parameters.items()):
        default = param.default
        if i < len(args) or field_name in kwargs:
            if isinstance(default, (AbstractProvider, StringProviderDefinition, _Provide)):
                injected = True
            continue

        if isinstance(default, StringProviderDefinition):
            injected = True
            kwargs[field_name] = _resolve_provider_with_scope_sync(default.provider, scope, stack, context_providers)
        elif isinstance(default, AbstractProvider):
            injected = True
            kwargs[field_name] = _resolve_provider_with_scope_sync(default, scope, stack, context_providers)
        elif isinstance(default, _Provide):
            injected = True
            if container is None:
                raise RuntimeError(_PROVIDE_MESSAGE)
            try:
                provider = container.get_provider_for_type(signature.parameters[field_name].annotation)
            except TypeNotBoundError as e:
                msg = f"Type {signature.parameters[field_name].annotation} is not bound to a provider."
                raise RuntimeError(msg) from e
            kwargs[field_name] = _resolve_provider_with_scope_sync(provider, scope, stack, context_providers)

    return injected, kwargs


def _resolve_sync(
    func: typing.Callable[P, T],
    scope: ContextScope | None,
    container: BaseContainerMeta | None = None,
    *args: P.args,
    **kwargs: P.kwargs,
) -> T:
    if func not in _SYNC_SIGNATURE_CACHE:
        with _THREADING_LOCK:
            _SYNC_SIGNATURE_CACHE[func] = inspect.signature(func)
    signature = _SYNC_SIGNATURE_CACHE[func]

    with ExitStack() as stack:
        injected, kwargs = _resolve_arguments_sync(signature, scope, container, stack, *args, **kwargs)  # type: ignore[assignment]

        if not injected:
            warnings.warn(_INJECTION_WARNING_MESSAGE, RuntimeWarning, stacklevel=1)

        return func(*args, **kwargs)


_SIGNATURE_CACHE: dict[
    typing.Callable[..., typing.Coroutine[typing.Any, typing.Any, typing.Any]], inspect.Signature
] = {}

_ASYNCIO_LOCK = asyncio.Lock()


async def _resolve_async(
    func: typing.Callable[P, typing.Coroutine[typing.Any, typing.Any, T]],
    scope: ContextScope | None,
    container: BaseContainerMeta | None = None,
    *args: P.args,
    **kwargs: P.kwargs,
) -> T:
    if func not in _SIGNATURE_CACHE:
        async with _ASYNCIO_LOCK:
            _SIGNATURE_CACHE[func] = inspect.signature(func)
    signature = _SIGNATURE_CACHE[func]

    async with AsyncExitStack() as stack:
        injected, kwargs = await _resolve_arguments_async(signature, scope, container, stack, *args, **kwargs)  # type: ignore[assignment]
        if not injected:
            warnings.warn(_INJECTION_WARNING_MESSAGE, RuntimeWarning, stacklevel=1)

        return await func(*args, **kwargs)

    raise RuntimeError  # pragma: no cover # to prevent mypy issue


async def _resolve_provider_with_scope_async(
    provider: AbstractProvider[T],
    scope: ContextScope | None,
    stack: AsyncExitStack | None,
    providers: set[AbstractProvider[typing.Any]],
) -> T:
    """Resolve a provider with given scope and stack.

    Use `stack=None` to ensure ContextResource providers are not allowed.

    Args:
        provider: provider to resolve.
        scope: scope to resolve provider in.
        stack: stack to use for context resources.
        providers: providers traversed.

    Returns:
        resolved value for the provider.

    Raises:
        ContextProviderError: if the stack is None.

    """
    await _add_provider_to_stack_async(provider, stack, scope, providers)
    return await provider.resolve()


async def _add_provider_to_stack_async(
    provider: AbstractProvider[T],
    stack: AsyncExitStack | None,
    scope: ContextScope | None,
    providers: set[AbstractProvider[typing.Any]],
) -> None:
    if provider in providers:
        return
    providers.add(provider)

    if not scope:
        return
    if isinstance(provider, ProviderWithArguments):
        provider._register_arguments()  # noqa: SLF001

        parents = provider._parents  # noqa: SLF001
        for parent in parents:
            await _add_provider_to_stack_async(parent, stack, scope, providers)
    if isinstance(provider, ContextResource):
        provider_scope = provider.get_scope()
        if provider_scope in (ContextScopes.ANY, scope):
            if stack is None:
                msg = (
                    f"No stack exists, cannot initialize context for {provider} using scope {scope}.\n"
                    f"Note: @inject cannot initialize context for ContextResources when wrapping a generator."
                )
                raise ContextProviderError(msg)
            await stack.enter_async_context(provider.context_async(force=True))


def _resolve_provider_with_scope_sync(
    provider: AbstractProvider[T],
    scope: ContextScope | None,
    stack: ExitStack | None,
    providers: set[AbstractProvider[typing.Any]],
) -> T:
    _add_provider_to_stack_sync(provider, stack, scope, providers)
    return provider.resolve_sync()


def _add_provider_to_stack_sync(
    provider: AbstractProvider[T],
    stack: ExitStack | None,
    scope: ContextScope | None,
    providers: set[AbstractProvider[typing.Any]],
) -> None:
    if provider in providers:
        return
    providers.add(provider)

    if not scope:
        return
    if isinstance(provider, ProviderWithArguments):
        provider._register_arguments()  # noqa: SLF001

        parents = provider._parents  # noqa: SLF001
        for parent in parents:
            _add_provider_to_stack_sync(parent, stack, scope, providers)

    if isinstance(provider, ContextResource):
        provider_scope = provider.get_scope()
        if provider_scope in (ContextScopes.ANY, scope):
            if stack is None:
                msg = (
                    f"No stack exists, cannot initialize context for {provider} using scope {scope}.\n"
                    f"Note: @inject cannot initialize context for ContextResources when wrapping a generator."
                )
                raise ContextProviderError(msg)
            stack.enter_context(provider.context_sync(force=True))


class StringProviderDefinition:
    """Provider definition from a string."""

    def __init__(self, definition: str) -> None:
        """Initialize the provider definition.

        Args:
            definition: provider definition in the format container.provider[.attr1.attr2...].

        """
        self._definition = definition
        self._container_name, self._provider_name, self._attrs = self._validate_and_extract_provider_definition()

    def _validate_and_extract_provider_definition(self) -> tuple[str, str, list[str]]:
        match = re.match(_STRING_PROVIDER_PATTERN, self._definition)
        if match:
            container_name = match.group(1)
            provider_name = match.group(2)
            attrs = match.group(3).split(".") if match.group(3) else []
            return container_name, provider_name, attrs
        msg = f"Invalid provider definition: {self._definition}"
        raise ValueError(msg)

    def _get_container_by_name(self) -> type["BaseContainer"]:
        containers_in_scope = BaseContainerMeta.get_instances()
        try:
            return containers_in_scope[self._container_name]
        except KeyError as e:
            msg = f"Container {self._container_name} not found in scope!"
            raise ValueError(msg) from e

    def _get_provider_by_name(self) -> AbstractProvider[typing.Any]:
        container = self._get_container_by_name()
        try:
            provider = container.get_providers()[self._provider_name]
        except KeyError as e:
            msg = f"Provider {self._provider_name} not found in container {self._container_name}"
            raise ValueError(msg) from e
        for attr in self._attrs:
            provider = getattr(provider, attr)
        return provider

    @property
    def provider(self) -> AbstractProvider[typing.Any]:
        """Get the provider instance."""
        return self._get_provider_by_name()


class _Provide:
    def __getitem__(self, provider: AbstractProvider[T] | str) -> T | typing.Any:  # noqa: ANN401
        if isinstance(provider, str):
            return StringProviderDefinition(provider)  # will be resolved later
        return typing.cast(T, provider)

    def __call__(self) -> typing.Any:  # noqa: ANN401
        """Marker for automatic dependency injection."""
        return self


Provide: typing.Final[_Provide] = _Provide()
