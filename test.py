import asyncio
import random
import typing

import pytest

from that_depends import BaseContainer, ContextScopes, Provide, inject, providers


async def _async_resource() -> typing.AsyncIterator[float]:
    yield random.random()


class _Container(BaseContainer):
    provider_used = providers.ContextResource(_async_resource).with_config(scope=ContextScopes.INJECT)
    provider_unused = providers.ContextResource(_async_resource).with_config(scope=ContextScopes.INJECT)


@inject
async def _injected(v: float = Provide[_Container.provider_used]) -> float:
    with pytest.raises(RuntimeError):
        assert await _Container.provider_unused.resolve()
    assert isinstance(v, float)
    return v


if __name__ == "__main__":
    asyncio.run(_injected())
