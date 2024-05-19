import functools
import inspect
import typing

from that_depends.providers import AbstractProvider


P = typing.ParamSpec("P")
T = typing.TypeVar("T")


def inject(
    func: typing.Callable[P, typing.Coroutine[typing.Any, typing.Any, T]],
) -> typing.Callable[P, typing.Coroutine[typing.Any, typing.Any, T]]:
    signature = inspect.signature(func)

    @functools.wraps(func)
    async def inner(*args: P.args, **kwargs: P.kwargs) -> T:
        for field_name, field_value in signature.parameters.items():
            if not isinstance(field_value.default, AbstractProvider):
                continue
            if field_name in kwargs:
                msg = f"Injected arguments must not be redefined, {field_name=}"
                raise RuntimeError(msg)

            kwargs[field_name] = await field_value.default()

        return await func(*args, **kwargs)

    return inner


class ClassGetItemMeta(type):
    def __getitem__(cls, provider: AbstractProvider[T]) -> T:
        return typing.cast(T, provider)


class Provide(metaclass=ClassGetItemMeta): ...
