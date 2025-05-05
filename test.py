import asyncio
import typing

from that_depends import BaseContainer, ContextScopes, Provide, get_current_scope, inject, providers


async def _async_creator() -> typing.AsyncIterator[float]:
    yield 1.0


class _Container(BaseContainer):
    resource = providers.ContextResource(_async_creator).with_config(scope=ContextScopes.INJECT)


@inject(scope=ContextScopes.INJECT)
async def _injected(x: float = Provide[_Container.resource]) -> float:
    current_scope = get_current_scope()
    assert current_scope is ContextScopes.INJECT
    return x


async def _main() -> None:
    await _injected()


if __name__ == "__main__":
    asyncio.run(_main())
