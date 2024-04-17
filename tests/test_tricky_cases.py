import logging

from that_depends import BaseContainer, providers


logger = logging.getLogger(__name__)


class TrickyDIContainer(BaseContainer):
    singleton = providers.Singleton(list)


async def test_singleton_with_empty_list() -> None:
    singleton1 = await TrickyDIContainer.singleton()
    singleton2 = await TrickyDIContainer.singleton()
    assert singleton1 is singleton2
