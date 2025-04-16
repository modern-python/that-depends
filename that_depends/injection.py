import asyncio
import functools
import inspect
import re
import threading
import typing
import warnings
from contextlib import AsyncExitStack, ExitStack

from that_depends.container import BaseContainer
from that_depends.meta import BaseContainerMeta
from that_depends.providers import AbstractProvider, ContextResource
from that_depends.providers.context_resources import ContextScope, ContextScopes
from that_depends.providers.mixin import ProviderWithArguments


P = typing.ParamSpec("P")
T = typing.TypeVar("T")
_STRING_PROVIDER_PATTERN = re.compile(r"^([^.]+)\.([^.]+)(?:\.(.+))?$")


@typing.overload
def inject(func: typing.Callable[P, T]) -> typing.Callable[P, T]: ...


@typing.overload
def inject(
    *,
    scope: ContextScope | None = ContextScopes.INJECT,
) -> typing.Callable[[typing.Callable[P, T]], typing.Callable[P, T]]: ...


def inject(
    func: typing.Callable[P, T] | None = None, scope: ContextScope | None = ContextScopes.INJECT
) -> typing.Callable[P, T] | typing.Callable[[typing.Callable[P, T]], typing.Callable[P, T]]:
    """Inject dependencies into a function."""
    if scope == ContextScopes.ANY:
        msg = f"{scope} is not allowed in inject decorator."
        raise ValueError(msg)

    def _inject(
        func: typing.Callable[P, T],
    ) -> typing.Callable[P, T]:
        if inspect.iscoroutinefunction(func):
            return typing.cast(typing.Callable[P, T], _inject_to_async(func))

        return _inject_to_sync(func)

    def _inject_to_async(
        func: typing.Callable[P, typing.Coroutine[typing.Any, typing.Any, T]],
    ) -> typing.Callable[P, typing.Coroutine[typing.Any, typing.Any, T]]:
        @functools.wraps(func)
        async def inner(*args: P.args, **kwargs: P.kwargs) -> T:
            return await _resolve_async(func, scope, *args, **kwargs)

        return inner

    def _inject_to_sync(
        func: typing.Callable[P, T],
    ) -> typing.Callable[P, T]:
        @functools.wraps(func)
        def inner(*args: P.args, **kwargs: P.kwargs) -> T:
            return _resolve_sync(func, scope, *args, **kwargs)

        return inner

    if func:
        return _inject(func)

    return _inject


_SYNC_SIGNATURE_CACHE: dict[typing.Callable[..., typing.Any], inspect.Signature] = {}
_THREADING_LOCK = threading.Lock()


def _resolve_sync(
    func: typing.Callable[P, T],
    scope: ContextScope | None,
    *args: P.args,
    **kwargs: P.kwargs,
) -> T:
    if func not in _SYNC_SIGNATURE_CACHE:
        with _THREADING_LOCK:
            _SYNC_SIGNATURE_CACHE[func] = inspect.signature(func)
    signature = _SYNC_SIGNATURE_CACHE[func]

    injected = False
    context_providers: set[AbstractProvider[typing.Any]] = set()

    with ExitStack() as stack:
        for i, (field_name, param) in enumerate(signature.parameters.items()):
            default = param.default

            if i < len(args) or field_name in kwargs:
                if isinstance(default, (AbstractProvider, StringProviderDefinition)):
                    injected = True
                continue

            if isinstance(default, StringProviderDefinition):
                injected = True
                kwargs[field_name] = _resolve_provider_with_scope_sync(
                    default.provider, scope, stack, context_providers
                )
            elif isinstance(default, AbstractProvider):
                injected = True
                kwargs[field_name] = _resolve_provider_with_scope_sync(default, scope, stack, context_providers)

        if not injected:
            warnings.warn(
                "Expected injection, but nothing found. Remove @inject decorator.", RuntimeWarning, stacklevel=1
            )

        return func(*args, **kwargs)


_SIGNATURE_CACHE: dict[
    typing.Callable[..., typing.Coroutine[typing.Any, typing.Any, typing.Any]], inspect.Signature
] = {}

_ASYNCIO_LOCK = asyncio.Lock()


async def _resolve_async(
    func: typing.Callable[P, typing.Coroutine[typing.Any, typing.Any, T]],
    scope: ContextScope | None,
    *args: P.args,
    **kwargs: P.kwargs,
) -> T:
    if func not in _SIGNATURE_CACHE:
        async with _ASYNCIO_LOCK:
            _SIGNATURE_CACHE[func] = inspect.signature(func)
    signature = _SIGNATURE_CACHE[func]

    injected = False
    context_providers: set[AbstractProvider[typing.Any]] = set()

    async with AsyncExitStack() as stack:
        params = list(signature.parameters.items())

        for i, (field_name, param) in enumerate(params):
            default = param.default

            if i < len(args) or field_name in kwargs:
                if isinstance(default, (AbstractProvider, StringProviderDefinition)):
                    injected = True
                continue

            if isinstance(default, StringProviderDefinition):
                injected = True
                resolved_val = await _resolve_provider_with_scope_async(
                    default.provider, scope, stack, context_providers
                )
                kwargs[field_name] = resolved_val
            elif isinstance(default, AbstractProvider):
                injected = True
                resolved_val = await _resolve_provider_with_scope_async(default, scope, stack, context_providers)
                kwargs[field_name] = resolved_val

        if not injected:
            warnings.warn(
                "Expected injection, but nothing found. Remove @inject decorator.", RuntimeWarning, stacklevel=1
            )

        return await func(*args, **kwargs)

    raise RuntimeError  # pragma: no cover # to prevent mypy issue


async def _resolve_provider_with_scope_async(
    provider: AbstractProvider[T],
    scope: ContextScope | None,
    stack: AsyncExitStack,
    providers: set[AbstractProvider[typing.Any]],
) -> T:
    await _add_provider_to_stack_async(provider, stack, scope, providers)
    return await provider.resolve()


async def _add_provider_to_stack_async(
    provider: AbstractProvider[T],
    stack: AsyncExitStack,
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
            await stack.enter_async_context(provider.context_async(force=True))


def _resolve_provider_with_scope_sync(
    provider: AbstractProvider[T],
    scope: ContextScope | None,
    stack: ExitStack,
    providers: set[AbstractProvider[typing.Any]],
) -> T:
    _add_provider_to_stack_sync(provider, stack, scope, providers)
    return provider.resolve_sync()


def _add_provider_to_stack_sync(
    provider: AbstractProvider[T],
    stack: ExitStack,
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


class ClassGetItemMeta(type):
    """Metaclass to support Provide[provider] syntax."""

    def __getitem__(cls, provider: AbstractProvider[T] | str) -> T | typing.Any:  # noqa: ANN401
        if isinstance(provider, str):
            return StringProviderDefinition(provider)  # will be resolved later
        return typing.cast(T, provider)


class Provide(metaclass=ClassGetItemMeta):
    """Marker to dependency injection."""
