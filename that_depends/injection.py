import functools
import inspect
import re
import typing
import warnings

from that_depends import BaseContainer
from that_depends.meta import BaseContainerMeta
from that_depends.providers import AbstractProvider
from that_depends.providers.context_resources import ContextScope, ContextScopes, container_context


P = typing.ParamSpec("P")
T = typing.TypeVar("T")


@typing.overload
def inject(func: typing.Callable[P, T]) -> typing.Callable[P, T]: ...


@typing.overload
def inject(
    *,
    scope: ContextScope | None = ContextScopes.INJECT,
) -> typing.Callable[[typing.Callable[P, T]], typing.Callable[P, T]]: ...


def inject(  # noqa: C901
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
            if scope:
                async with container_context(scope=scope):
                    return await _resolve_async(func, *args, **kwargs)
            return await _resolve_async(func, *args, **kwargs)

        return inner

    def _inject_to_sync(
        func: typing.Callable[P, T],
    ) -> typing.Callable[P, T]:
        @functools.wraps(func)
        def inner(*args: P.args, **kwargs: P.kwargs) -> T:
            if scope:
                with container_context(scope=scope):
                    return _resolve_sync(func, *args, **kwargs)
            return _resolve_sync(func, *args, **kwargs)

        return inner

    if func:
        return _inject(func)

    return _inject


def _resolve_sync(func: typing.Callable[P, T], *args: P.args, **kwargs: P.kwargs) -> T:
    injected = False
    signature: typing.Final = inspect.signature(func)
    for i, (field_name, field_value) in enumerate(signature.parameters.items()):
        if i < len(args):
            continue
        if not isinstance(field_value.default, AbstractProvider):
            continue
        if field_name in kwargs:
            if isinstance(field_value.default, AbstractProvider):
                injected = True
            continue
        kwargs[field_name] = field_value.default.sync_resolve()
        injected = True

    if not injected:
        warnings.warn("Expected injection, but nothing found. Remove @inject decorator.", RuntimeWarning, stacklevel=1)

    return func(*args, **kwargs)


async def _resolve_async(
    func: typing.Callable[P, typing.Coroutine[typing.Any, typing.Any, T]], *args: P.args, **kwargs: P.kwargs
) -> T:
    injected = False
    signature = inspect.signature(func)
    for i, (field_name, field_value) in enumerate(signature.parameters.items()):
        if i < len(args):
            if isinstance(field_value.default, AbstractProvider):
                injected = True
            continue

        if not isinstance(field_value.default, AbstractProvider):
            continue

        if field_name in kwargs:
            if isinstance(field_value.default, AbstractProvider):
                injected = True
            continue

        kwargs[field_name] = await field_value.default.async_resolve()
        injected = True
    if not injected:
        warnings.warn("Expected injection, but nothing found. Remove @inject decorator.", RuntimeWarning, stacklevel=1)
    return await func(*args, **kwargs)


def _get_provider_by_name(name: str) -> AbstractProvider[typing.Any]:
    container_name, provider_name, attrs = _validate_and_extract_provider_definition(name)
    container = _get_container_by_name(container_name)
    try:
        provider = container.get_providers()[provider_name]
    except KeyError as e:
        msg = f"Provider {provider_name} not found in container {container_name}"
        raise ValueError(msg) from e
    for attr in attrs:
        provider = getattr(provider, attr)
    return provider


def _get_container_by_name(name: str) -> type["BaseContainer"]:
    containers_in_scope = BaseContainerMeta.get_instances()
    try:
        return containers_in_scope[name]
    except KeyError as e:
        msg = f"Container {name} not found in scope!"
        raise ValueError(msg) from e


def _validate_and_extract_provider_definition(definition: str) -> tuple[str, str, list[str]]:
    pattern = r"^([^.]+)\.([^.]+)(?:\.(.+))?$"
    match = re.match(pattern, definition)
    if match:
        container_name = match.group(1)
        provider_name = match.group(2)
        attrs = match.group(3).split(".") if match.group(3) else []
        return container_name, provider_name, attrs
    msg = f"Invalid provider definition: {definition}"
    raise ValueError(msg)


class ClassGetItemMeta(type):
    """Metaclass to support Provide[provider] syntax."""

    def __getitem__(cls, provider: AbstractProvider[T] | str) -> T | typing.Any:  # noqa: ANN401
        if isinstance(provider, str):
            return _get_provider_by_name(provider)
        return typing.cast(T, provider)


class Provide(metaclass=ClassGetItemMeta):
    """Marker to dependency injection."""
