import random

from that_depends import BaseContainer, Provide, inject, providers


async def test_async_factory_with_sync_creator() -> None:
    return_value = random.random()
    f = providers.AsyncFactory(lambda: return_value)

    assert await f.resolve() == return_value


async def test_async_factory_with_sync_creator_multiple_parents() -> None:
    """Dependencies of async factory get resolved correctly with a sync creator."""
    _return_value_1 = 32
    _return_value_2 = 12

    async def _async_creator() -> int:
        return 32

    def _sync_creator() -> int:
        return _return_value_2

    class _Adder:
        def __init__(self, x: int, y: int) -> None:
            self.x = x
            self.y = y

        def result(self) -> int:
            return self.x + self.y

    class _Container(BaseContainer):
        p1 = providers.AsyncFactory(_async_creator)
        p2 = providers.Factory(_sync_creator)
        p3 = providers.AsyncFactory(_Adder, x=p1.cast, y=p2.cast)

    @inject
    async def _injected(adder: _Adder = Provide[_Container.p3]) -> int:
        return adder.result()

    assert await _injected() == _return_value_1 + _return_value_2
