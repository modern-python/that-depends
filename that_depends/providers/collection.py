import typing

from that_depends.providers.base import AbstractProvider


T_co = typing.TypeVar("T_co", covariant=True)


class List(AbstractProvider[list[T_co]]):
    __slots__ = ("_providers",)

    def __init__(self, *providers: AbstractProvider[T_co]) -> None:
        super().__init__()
        self._providers: typing.Final = providers

    def __getattr__(self, attr_name: str) -> typing.Any:  # noqa: ANN401
        msg = f"'{type(self)}' object has no attribute '{attr_name}'"
        raise AttributeError(msg)

    async def async_resolve(self) -> list[T_co]:
        return [await x.async_resolve() for x in self._providers]

    def sync_resolve(self) -> list[T_co]:
        return [x.sync_resolve() for x in self._providers]

    async def __call__(self) -> list[T_co]:
        return await self.async_resolve()


class Dict(AbstractProvider[dict[str, T_co]]):
    __slots__ = ("_providers",)

    def __init__(self, **providers: AbstractProvider[T_co]) -> None:
        super().__init__()
        self._providers: typing.Final = providers

    def __getattr__(self, attr_name: str) -> typing.Any:  # noqa: ANN401
        msg = f"'{type(self)}' object has no attribute '{attr_name}'"
        raise AttributeError(msg)

    async def async_resolve(self) -> dict[str, T_co]:
        return {key: await provider.async_resolve() for key, provider in self._providers.items()}

    def sync_resolve(self) -> dict[str, T_co]:
        return {key: provider.sync_resolve() for key, provider in self._providers.items()}
