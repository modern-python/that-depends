import asyncio
from collections.abc import AsyncGenerator
from contextlib import asynccontextmanager

from that_depends import BaseContainer, Provide, inject, providers


_EXPECTED_RETURN_VALUE = "hello"


async def _async_creator() -> str:
    return _EXPECTED_RETURN_VALUE


class _Container(BaseContainer):
    factory = providers.AsyncFactory(_async_creator)
    dependent_factory = providers.Factory(lambda x: x, factory.cast)


@inject
async def _generator(
    v_1: str = Provide[_Container.factory], v_2: str = Provide[_Container.dependent_factory]
) -> AsyncGenerator[str, None]:
    yield v_1 + v_2


ctx = asynccontextmanager(_generator)


async def _main() -> None:
    assert await anext(_generator()) == _EXPECTED_RETURN_VALUE + _EXPECTED_RETURN_VALUE
    async with ctx() as v:
        assert v == _EXPECTED_RETURN_VALUE + _EXPECTED_RETURN_VALUE


if __name__ == "__main__":
    asyncio.run(_main())
