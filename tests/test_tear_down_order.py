import asyncio
import typing
from dataclasses import dataclass

import pytest

from that_depends import BaseContainer, providers
from that_depends.providers.context_resources import container_context


@dataclass
class Dependency:
    attr: int


def singleton(**_kwargs: providers.AbstractProvider[typing.Any]) -> Dependency:
    return Dependency(0)


async def async_factory(**_kwargs: providers.AbstractProvider[typing.Any]) -> Dependency:
    return Dependency(0)


async def async_resource(
    name: str,
    order: list[str],
    **_kwargs: providers.AbstractProvider[typing.Any],
) -> typing.AsyncIterator[str]:
    yield name
    await asyncio.sleep(0.01)  # To simulate some IO during teardown
    order.append(name)


def sync_resource(
    name: str,
    order: list[str],
    **_kwargs: providers.AbstractProvider[typing.Any],
) -> typing.Iterator[str]:
    yield name
    order.append(name)


class Container1(BaseContainer):
    order = providers.Singleton(list[str])
    object = providers.Object(42)
    a = providers.AsyncResource(async_resource, "A", order=order.cast, object=object)


class Container2(BaseContainer):
    order = providers.Singleton(list[str])
    a = providers.AsyncResource(async_resource, "A", order=order.cast)
    b = providers.Resource(sync_resource, "B", order=order.cast, a=a)


class Container3(BaseContainer):
    order = providers.Singleton(list[str])
    a = providers.AsyncResource(async_resource, "A", order=order.cast)
    b = providers.Resource(sync_resource, "B", order=order.cast, a=a)
    c = providers.AsyncResource(async_resource, "C", order=order.cast, b=b)
    d = providers.Resource(sync_resource, "D", order=order.cast, b=b, c=c)


class Container4(BaseContainer):
    order = providers.Singleton(list[str])
    a = providers.AsyncResource(async_resource, "A", order=order.cast)
    b = providers.Singleton(singleton, a=a)
    c = providers.AsyncResource(async_resource, "C", order=order.cast, b=b)


class Container5(BaseContainer):
    order = providers.Singleton(list[str])
    a = providers.AsyncResource(async_resource, "A", order=order.cast)
    b = providers.Singleton(singleton, a=a)
    c = providers.AsyncResource(async_resource, "C", order=order.cast, b_attr=b.attr)
    d = providers.AsyncResource(async_resource, "D", order=order.cast, c=c)


class Container6(BaseContainer):
    order = providers.Singleton(list[str])
    a = providers.AsyncResource(async_resource, "A", order=order.cast)
    b = providers.Resource(sync_resource, "B", order=order.cast, a=a)
    c = providers.AsyncResource(async_resource, "C", order=order.cast)
    d = providers.Resource(sync_resource, "D", order=order.cast, c=c, a=a)
    e = providers.AsyncResource(async_resource, "E", order=order.cast, d=d)


class Container7(BaseContainer):
    order = providers.Singleton(list[str])
    a = providers.Resource(sync_resource, "A", order=order.cast)
    b = providers.Singleton(singleton, a=a)
    c = providers.AsyncResource(async_resource, "C", order=order.cast, b=b)
    d = providers.Singleton(singleton, c=c)
    e = providers.AsyncResource(async_resource, "E", order=order.cast)
    f = providers.AsyncResource(async_resource, "F", order=order.cast, d=d)


class Container8(BaseContainer):
    order = providers.Singleton(list[str])
    a = providers.Resource(sync_resource, "A", order=order.cast)
    b = providers.Factory(str, a)
    c = providers.AsyncFactory(async_factory, b=b)
    d = providers.AsyncResource(async_resource, "C", order=order.cast, c=c)


class Container9(BaseContainer):
    order = providers.Singleton(list[str])
    a = providers.Resource(sync_resource, "A", order=order.cast)
    b = providers.Resource(sync_resource, "B", order=order.cast)
    c = providers.List(a, b)
    d = providers.AsyncResource(async_resource, "D", order=order.cast, c=c)


class Container10(BaseContainer):
    order = providers.Singleton(list[str])
    a = providers.Resource(sync_resource, "A", order=order.cast)
    b = providers.Resource(sync_resource, "B", order=order.cast, a=a)
    c = providers.AsyncResource(async_resource, "C", order=order.cast)
    d = providers.Dict(a=a, b=b, c=c)
    e = providers.AsyncResource(async_resource, "E", order=order.cast, d=d)


class Container11(BaseContainer):
    order = providers.Singleton(list[str])
    a = providers.Resource(sync_resource, "A", order=order.cast)
    b = providers.AsyncResource(async_resource, "B", order=order.cast)
    c = providers.Selector(lambda: "a", a=a, b=b)
    d = providers.Resource(sync_resource, "D", order=order.cast, c=c)
    e = providers.AsyncResource(async_resource, "E", order=order.cast, c=c)


@pytest.mark.parametrize(
    ("container", "expected_order"),
    [
        pytest.param(Container1, ["A"], id="1"),
        pytest.param(Container2, ["B", "A"], id="2"),
        pytest.param(Container3, ["D", "C", "B", "A"], id="3"),
        pytest.param(Container4, ["C", "A"], id="4"),
        pytest.param(Container5, ["D", "C", "A"], id="5"),
        pytest.param(Container6, ["B", "E", "D", "A", "C"], id="6"),
        pytest.param(Container7, ["E", "F", "C", "A"], id="7"),
        pytest.param(Container8, ["C", "A"], id="8"),
        pytest.param(Container9, ["D", "A", "B"], id="9"),
        pytest.param(Container10, ["E", "B", "C", "A"], id="10"),
        pytest.param(Container11, ["D", "E", "A", "B"], id="11"),
    ],
)
async def test_tear_down_order(container: type[BaseContainer], expected_order: list[str]) -> None:
    await container.init_async_resources()
    order = await container.order()  # type: ignore[attr-defined]

    await container.tear_down()

    assert order == expected_order


class ContextContainer1(BaseContainer):
    order = providers.Singleton(list[str])
    a = providers.AsyncContextResource(async_resource, "A", order=order.cast)
    init = providers.AsyncFactory(async_factory, a=a)


class ContextContainer2(BaseContainer):
    order = providers.Singleton(list[str])
    a = providers.AsyncContextResource(async_resource, "A", order=order.cast)
    b = providers.ContextResource(sync_resource, "B", order=order.cast, a=a)
    init = providers.AsyncFactory(async_factory, b=b)


class ContextContainer3(BaseContainer):
    order = providers.Singleton(list[str])
    a = providers.AsyncContextResource(async_resource, "A", order=order.cast)
    b = providers.AsyncFactory(async_factory, a=a)
    c = providers.AsyncContextResource(async_resource, "C", order=order.cast, b=b)
    d = providers.AsyncFactory(async_factory, c=c)
    e = providers.AsyncContextResource(async_resource, "E", order=order.cast, d=d)
    init = providers.AsyncFactory(async_factory, e=e)


@pytest.mark.parametrize(
    ("container", "expected_order"),
    [
        pytest.param(ContextContainer1, ["A"], id="1"),
        pytest.param(ContextContainer2, ["B", "A"], id="2"),
        pytest.param(ContextContainer3, ["E", "C", "A"], id="3"),
    ],
)
async def test_tear_down_order_for_context_resources(container: type[BaseContainer], expected_order: list[str]) -> None:
    await container.init_async_resources()
    order = await container.order()  # type: ignore[attr-defined]

    async with container_context():
        await container.init()  # type: ignore[attr-defined]

    assert order == expected_order
