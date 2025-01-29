import functools
import inspect
import typing
import warnings

from that_depends.providers import AbstractProvider
from that_depends.providers.context_resources import ContextScope, container_context


P = typing.ParamSpec("P")
T = typing.TypeVar("T")


@typing.overload
def inject(func: typing.Callable[P, T]) -> typing.Callable[P, T]: ...


@typing.overload
def inject(
    *,
    scope: ContextScope | None = None,
) -> typing.Callable[[typing.Callable[P, T]], typing.Callable[P, T]]: ...


def inject(  # noqa: C901
    func: typing.Callable[P, T] | None = None, scope: ContextScope | None = None
) -> typing.Callable[P, T] | typing.Callable[[typing.Callable[P, T]], typing.Callable[P, T]]:
    """Inject dependencies into a function."""
    if scope == ContextScope.ANY:
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
        signature = inspect.signature(func)

        @functools.wraps(func)
        async def inner(*args: P.args, **kwargs: P.kwargs) -> T:
            injected = False
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
                warnings.warn(
                    "Expected injection, but nothing found. Remove @inject decorator.", RuntimeWarning, stacklevel=1
                )
            if scope:
                async with container_context(scope=scope):
                    return await func(*args, **kwargs)
            return await func(*args, **kwargs)

        return inner

    def _inject_to_sync(
        func: typing.Callable[P, T],
    ) -> typing.Callable[P, T]:
        signature: typing.Final = inspect.signature(func)

        @functools.wraps(func)
        def inner(*args: P.args, **kwargs: P.kwargs) -> T:
            injected = False
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
                warnings.warn(
                    "Expected injection, but nothing found. Remove @inject decorator.", RuntimeWarning, stacklevel=1
                )
            if scope:
                with container_context(scope=scope):
                    return func(*args, **kwargs)
            return func(*args, **kwargs)

        return inner

    if func:
        return _inject(func)

    return _inject


class ClassGetItemMeta(type):
    """Metaclass to support Provide[provider] syntax."""

    def __getitem__(cls, provider: AbstractProvider[T]) -> T:
        return typing.cast(T, provider)


class Provide(metaclass=ClassGetItemMeta):
    """Marker to dependency injection."""
