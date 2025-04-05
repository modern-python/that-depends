import functools
import inspect
import re
import typing
import warnings
from contextlib import AsyncExitStack, ExitStack

from that_depends.container import BaseContainer
from that_depends.meta import BaseContainerMeta
from that_depends.providers import AbstractProvider, ContextResource
from that_depends.providers.context_resources import ContextScope, ContextScopes


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


def _resolve_sync(func: typing.Callable[P, T], scope: ContextScope | None, *args: P.args, **kwargs: P.kwargs) -> T:
    injected = False
    signature: typing.Final = inspect.signature(func)
    context_providers: set[AbstractProvider[typing.Any]] = set()
    with ExitStack() as stack:
        for i, (field_name, field_value) in enumerate(signature.parameters.items()):
            if i < len(args):
                continue
            if not isinstance(field_value.default, AbstractProvider) and not isinstance(
                field_value.default, StringProviderDefinition
            ):
                continue
            if field_name in kwargs:
                if isinstance(field_value.default, AbstractProvider | StringProviderDefinition):
                    injected = True
                continue
            if isinstance(field_value.default, StringProviderDefinition):
                kwargs[field_name] = _resolve_provider_with_scope_sync(
                    field_value.default.provider, scope=scope, stack=stack, providers=context_providers
                )
            else:
                kwargs[field_name] = _resolve_provider_with_scope_sync(
                    field_value.default, scope=scope, stack=stack, providers=context_providers
                )
            injected = True

        if not injected:
            warnings.warn(
                "Expected injection, but nothing found. Remove @inject decorator.", RuntimeWarning, stacklevel=1
            )

        return func(*args, **kwargs)


async def _resolve_async(  # typing: ignore
    func: typing.Callable[P, typing.Coroutine[typing.Any, typing.Any, T]],
    scope: ContextScope | None,
    *args: P.args,
    **kwargs: P.kwargs,
) -> T:
    injected = False
    signature = inspect.signature(func)
    context_providers: set[AbstractProvider[typing.Any]] = set()
    async with AsyncExitStack() as stack:
        for i, (field_name, field_value) in enumerate(signature.parameters.items()):
            if i < len(args):
                if isinstance(field_value.default, AbstractProvider | StringProviderDefinition):
                    injected = True
                continue

            if not isinstance(field_value.default, AbstractProvider) and not isinstance(
                field_value.default, StringProviderDefinition
            ):
                continue

            if field_name in kwargs:
                if isinstance(field_value.default, AbstractProvider | StringProviderDefinition):
                    injected = True
                continue
            if isinstance(field_value.default, StringProviderDefinition):
                kwargs[field_name] = await _resolve_provider_with_scope_async(
                    field_value.default.provider, scope=scope, stack=stack, providers=context_providers
                )
            else:  # AbstractProvider
                kwargs[field_name] = await _resolve_provider_with_scope_async(
                    field_value.default, scope=scope, stack=stack, providers=context_providers
                )
            injected = True
        if not injected:
            warnings.warn(
                "Expected injection, but nothing found. Remove @inject decorator.", RuntimeWarning, stacklevel=1
            )
        return await func(*args, **kwargs)
    raise RuntimeError  # pragma: no cover # for mypy, otherwise unreachable


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
    if isinstance(provider, ContextResource) and scope:
        provider_scope = provider.get_scope()
        if provider_scope in (ContextScopes.ANY, scope):
            provider._register_arguments()  # noqa: SLF001
            for parent in provider._parents:  # noqa: SLF001
                await _add_provider_to_stack_async(parent, stack, scope, providers)
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
    if isinstance(provider, ContextResource) and scope:
        provider_scope = provider.get_scope()
        if provider_scope in (ContextScopes.ANY, scope):
            provider._register_arguments()  # noqa: SLF001
            for parent in provider._parents:  # noqa: SLF001
                _add_provider_to_stack_sync(parent, stack, scope, providers)
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
