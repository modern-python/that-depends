import asyncio
import typing

import that_depends
from that_depends import container_context, providers


async def test_race_condition_in_resource() -> None:
    calls: int = 0

    async def create_resource() -> typing.AsyncIterator[str]:
        nonlocal calls
        calls += 1
        await asyncio.sleep(0)
        yield ""

    class IOCContainer(that_depends.BaseContainer):
        resource = providers.Resource(create_resource)

    @that_depends.inject
    async def uses_resource(_: str = that_depends.Provide[IOCContainer.resource]) -> None: ...

    await asyncio.gather(uses_resource(), uses_resource())

    assert calls == 1


async def test_race_condition_in_async_resource() -> None:
    calls: int = 0

    async def create_client() -> typing.AsyncIterator[str]:
        nonlocal calls
        calls += 1
        await asyncio.sleep(0)
        yield ""

    class IOCContainer(that_depends.BaseContainer):
        client = providers.ContextResource(create_client)

    @that_depends.inject
    async def uses_client(_: str = that_depends.Provide[IOCContainer.client]) -> None: ...

    async with container_context():
        await asyncio.gather(uses_client(), uses_client())

    assert calls == 1
