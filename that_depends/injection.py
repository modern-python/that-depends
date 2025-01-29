import functools
import inspect
import typing
import warnings

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


class ClassGetItemMeta(type):
    """Metaclass to support Provide[provider] syntax."""

    def __getitem__(cls, provider: AbstractProvider[T]) -> T:
        return typing.cast(T, provider)


class Provide(metaclass=ClassGetItemMeta):
    """Marker to dependency injection."""
