import logging
import random
import time
import typing

from that_depends import BaseContainer, ContextScopes, Provide, inject, providers


logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


def _iterator(x: float) -> typing.Iterator[float]:
    yield x


class _Container(BaseContainer):
    grandparent = providers.Singleton(lambda: random.random())
    parent = providers.Factory(lambda x: x, grandparent.cast)
    item = providers.ContextResource(_iterator, parent.cast).with_config(scope=ContextScopes.REQUEST)


@inject(scope=ContextScopes.REQUEST)
def _injected(
    x_1: float = Provide[_Container.grandparent],
    x_2: float = Provide[_Container.parent],
    x_3: float = Provide[_Container.item],
) -> float:
    return x_1 + x_2 + x_3


def _bench(n_iterations: int) -> float:
    start = time.time()
    for _ in range(n_iterations):
        _injected()
    end = time.time()
    _Container.tear_down_sync()
    return end - start


if __name__ == "__main__":
    for n in [10000, 100000, 1000000]:
        duration = _bench(n)
        logger.info(f"Injected {n} times in {duration:.4f} seconds")  # noqa: G004
