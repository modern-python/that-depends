import typing

from typing_extensions import override

from that_depends.providers.base import AbstractProvider


T_co = typing.TypeVar("T_co", covariant=True)
P = typing.ParamSpec("P")


class Object(AbstractProvider[T_co]):
    """Provides an object "as is" without any modification.

    This provider always returns the same object that was given during
    initialization.

    Example:
        ```python
        provider = Object(1)
        result = provider.sync_resolve()
        print(result)  # 1
        ```

    """

    __slots__ = ("_obj",)

    def __init__(self, obj: T_co) -> None:
        """Initialize the provider with the given object.

        Args:
            obj (T_co): The object to be provided.

        """
        super().__init__()
        self._obj: typing.Final = obj

    @override
    async def async_resolve(self) -> T_co:
        return self.sync_resolve()

    @override
    def sync_resolve(self) -> T_co:
        if self._override is not None:
            return typing.cast(T_co, self._override)
        return self._obj
