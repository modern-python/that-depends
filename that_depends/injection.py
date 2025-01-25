import functools
import inspect
import typing
import warnings

from that_depends.providers import AbstractProvider


P = typing.ParamSpec("P")
T = typing.TypeVar("T")


def inject(
    func: typing.Callable[P, T],
) -> typing.Callable[P, T]:
    """Decorate a function to enable dependency injection.

    Args:
        func: sync or async function with dependencies.

    Returns:
        function that will resolve dependencies on call.


    Example:
        ```python
        @inject
        async def func(a: str = Provide[Container.a_provider]) -> str:
            ...
        ```

    """
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

        return func(*args, **kwargs)

    return inner


class ClassGetItemMeta(type):
    """Metaclass to support Provide[provider] syntax."""

    def __getitem__(cls, provider: AbstractProvider[T]) -> T:
        return typing.cast(T, provider)


class Provide(metaclass=ClassGetItemMeta):
    """Marker to dependency injection."""
