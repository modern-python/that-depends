import asyncio
import typing
from contextlib import asynccontextmanager, contextmanager

import pytest

from that_depends import providers


_VALUE = 42


async def _switch_routines() -> None:
    await asyncio.sleep(0.0)


class SimpleCM(typing.AsyncContextManager[int]):
    async def __aenter__(self) -> int:
        await _switch_routines()
        return _VALUE

    async def __aexit__(self, exc_type: object, exc_value: object, traceback: object, /) -> bool | None:
        await _switch_routines()
        return None


class SimpleCMSync(typing.ContextManager[int]):
    def __enter__(self) -> int:
        return _VALUE

    def __exit__(self, exc_type: object, exc_value: object, traceback: object, /) -> bool | None:
        return None


@asynccontextmanager
async def do_stuff_cm() -> typing.AsyncIterator[int]:
    await _switch_routines()
    yield _VALUE
    await _switch_routines()


@contextmanager
def do_stuff_cm_sync() -> typing.Iterator[int]:
    yield _VALUE


async def do_stuff_it() -> typing.AsyncIterator[int]:
    await _switch_routines()
    yield _VALUE
    await _switch_routines()


def do_stuff_it_sync() -> typing.Iterator[int]:
    yield _VALUE


@pytest.mark.parametrize(
    "resource",
    [
        pytest.param(providers.Resource(SimpleCM()), id="cm_simple"),
        pytest.param(providers.Resource(SimpleCMSync()), id="cm_simple_sync"),
        pytest.param(providers.Resource(do_stuff_cm), id="cm_factory"),
        pytest.param(providers.Resource(do_stuff_cm_sync), id="cm_sync_factory"),
        pytest.param(providers.Resource(do_stuff_it), id="cm_iterator"),
        pytest.param(providers.Resource(do_stuff_it_sync), id="cm_sync_iterator"),
    ],
)
async def test_resource_async_resolve_works(resource: providers.Resource[int]) -> None:
    instance = await resource.async_resolve()
    assert instance == _VALUE
