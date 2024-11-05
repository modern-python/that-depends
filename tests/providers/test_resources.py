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


@pytest.mark.parametrize(
    "resource",
    [
        pytest.param(providers.Resource(SimpleCMSync()), id="cm_simple_sync"),
        pytest.param(providers.Resource(do_stuff_cm_sync), id="cm_sync_factory"),
        pytest.param(providers.Resource(do_stuff_it_sync), id="cm_sync_iterator"),
    ],
)
def test_resource_sync_resolve_works(resource: providers.Resource[int]) -> None:
    instance = resource.sync_resolve()
    assert instance == _VALUE


@pytest.mark.parametrize(
    "resource",
    [
        pytest.param(providers.Resource(SimpleCM()), id="cm_simple"),
        pytest.param(providers.Resource(do_stuff_cm), id="cm_factory"),
        pytest.param(providers.Resource(do_stuff_it), id="cm_iterator"),
    ],
)
def test_resource_sync_resolve_is_not_possible_for_async_context_manager(resource: providers.Resource[int]) -> None:
    with pytest.raises(TypeError, match="A ContextManager type was expected in synchronous resolve"):
        resource.sync_resolve()


async def do_invalid_creator_stuff_simple_coro_func() -> None:
    pass


async def do_invalid_creator_stuff_inner_func() -> typing.Callable[[], typing.Awaitable[int]]:
    async def do_stuff_inner() -> int:
        return 42

    return do_stuff_inner


# NOTE: this is a special case for resource creator normalizer, it has to be invalid, because return type annotation is
# not specified here.
@asynccontextmanager
async def do_invalid_creator_stuff_cm_without_annotation():  # type: ignore[no-untyped-def] # noqa: ANN201
    await _switch_routines()
    yield _VALUE
    await _switch_routines()


@pytest.mark.parametrize(
    ("creator", "args", "kwargs", "error_msg"),
    [
        pytest.param(
            42,
            (),
            {},
            "Creator is not of a valid type",
            id="int",
        ),
        pytest.param(
            do_invalid_creator_stuff_simple_coro_func,
            (),
            {},
            "Creator is not of a valid type",
            id="simple coroutine func",
        ),
        pytest.param(
            do_invalid_creator_stuff_inner_func,
            (),
            {},
            "Creator is not of a valid type",
            id="inner coroutine func",
        ),
        pytest.param(
            do_invalid_creator_stuff_cm_without_annotation,
            (),
            {},
            "Creator is not of a valid type",
            id="cm without annotation",
        ),
        pytest.param(
            SimpleCM(),
            (),
            {"param": "not acceptable for CM"},
            "AsyncContextManager does not accept any arguments",
            id="CM with param",
        ),
        pytest.param(
            SimpleCMSync(),
            (),
            {"param": "not acceptable for CM"},
            "ContextManager does not accept any arguments",
            id="sync CM with param",
        ),
    ],
)
async def test_resource_init_raises_type_error_on_invalid_arguments(
    # NOTE: testing inappropriate types here, so using Any in annotations.
    creator: typing.Any,  # noqa: ANN401
    args: typing.Sequence[object],
    kwargs: typing.Mapping[str, object],
    error_msg: str,
) -> None:
    with pytest.raises(TypeError, match=error_msg):
        providers.Resource(creator, *args, **kwargs)
