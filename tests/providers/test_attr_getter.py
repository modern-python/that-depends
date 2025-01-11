import random
import typing
from dataclasses import dataclass, field

import pytest

from that_depends import providers
from that_depends.providers.base import _get_value_from_object_by_dotted_path
from that_depends.providers.context_resources import container_context


@dataclass
class Nested2:
    some_const = 144


@dataclass
class Nested1:
    nested2_attr: Nested2 = field(default_factory=Nested2)


@dataclass
class Settings:
    some_str_value: str = "some_string_value"
    some_int_value: int = 3453621
    nested1_attr: Nested1 = field(default_factory=Nested1)


async def return_settings_async() -> Settings:
    return Settings()


async def yield_settings_async() -> typing.AsyncIterator[Settings]:
    yield Settings()


def yield_settings_sync() -> typing.Iterator[Settings]:
    yield Settings()


@dataclass
class NestingTestDTO: ...


@pytest.fixture(
    params=[
        providers.Resource(yield_settings_sync),
        providers.Singleton(Settings),
        providers.ContextResource(yield_settings_sync),
        providers.Object(Settings()),
        providers.Factory(Settings),
        providers.Selector(lambda: "sync", sync=providers.Factory(Settings)),
    ]
)
def some_sync_settings_provider(request: pytest.FixtureRequest) -> providers.AbstractProvider[Settings]:
    return typing.cast(providers.AbstractProvider[Settings], request.param)


@pytest.fixture(
    params=[
        providers.AsyncFactory(return_settings_async),
        providers.Resource(yield_settings_async),
        providers.ContextResource(yield_settings_async),
        providers.Selector(lambda: "asynchronous", asynchronous=providers.AsyncFactory(return_settings_async)),
    ]
)
def some_async_settings_provider(request: pytest.FixtureRequest) -> providers.AbstractProvider[Settings]:
    return typing.cast(providers.AbstractProvider[Settings], request.param)


def test_attr_getter_with_zero_attribute_depth_sync(
    some_sync_settings_provider: providers.AbstractProvider[Settings],
) -> None:
    attr_getter = some_sync_settings_provider.some_str_value
    if isinstance(some_sync_settings_provider, providers.ContextResource):
        with container_context(some_sync_settings_provider):
            assert attr_getter.sync_resolve() == Settings().some_str_value
    else:
        assert attr_getter.sync_resolve() == Settings().some_str_value


async def test_attr_getter_with_zero_attribute_depth_async(
    some_async_settings_provider: providers.AbstractProvider[Settings],
) -> None:
    attr_getter = some_async_settings_provider.some_str_value
    if isinstance(some_async_settings_provider, providers.ContextResource):
        async with container_context(some_async_settings_provider):
            assert await attr_getter.async_resolve() == Settings().some_str_value
    else:
        assert await attr_getter.async_resolve() == Settings().some_str_value


def test_attr_getter_with_more_than_zero_attribute_depth_sync(
    some_sync_settings_provider: providers.AbstractProvider[Settings],
) -> None:
    with (
        container_context(some_sync_settings_provider)
        if isinstance(some_sync_settings_provider, providers.ContextResource)
        else container_context()
    ):
        attr_getter = some_sync_settings_provider.nested1_attr.nested2_attr.some_const
        assert attr_getter.sync_resolve() == Nested2().some_const


async def test_attr_getter_with_more_than_zero_attribute_depth_async(
    some_async_settings_provider: providers.AbstractProvider[Settings],
) -> None:
    async with (
        container_context(some_async_settings_provider)
        if isinstance(some_async_settings_provider, providers.ContextResource)
        else container_context()
    ):
        attr_getter = some_async_settings_provider.nested1_attr.nested2_attr.some_const
        assert await attr_getter.async_resolve() == Nested2().some_const


@pytest.mark.parametrize(
    ("field_count", "test_field_name", "test_value"),
    [(1, "test_field", "sdf6fF^SF(FF*4ffsf"), (5, "nested_field", -252625), (50, "50_lvl_field", 909234235)],
)
def test_nesting_levels(field_count: int, test_field_name: str, test_value: str | int) -> None:
    obj = NestingTestDTO()
    fields = [f"field_{i}" for i in range(1, field_count + 1)]
    random.shuffle(fields)

    attr_path = ".".join(fields) + f".{test_field_name}"
    obj_copy = obj

    while fields:
        field_name = fields.pop(0)
        setattr(obj_copy, field_name, NestingTestDTO())
        obj_copy = obj_copy.__getattribute__(field_name)

    setattr(obj_copy, test_field_name, test_value)

    attr_value = _get_value_from_object_by_dotted_path(obj, attr_path)
    assert attr_value == test_value


@container_context()
def test_attr_getter_with_invalid_attribute_sync(
    some_sync_settings_provider: providers.AbstractProvider[Settings],
) -> None:
    with pytest.raises(AttributeError):
        some_sync_settings_provider.nested1_attr.nested2_attr.__some_private__  # noqa: B018
    with pytest.raises(AttributeError):
        some_sync_settings_provider.nested1_attr.__another_private__  # noqa: B018
    with pytest.raises(AttributeError):
        some_sync_settings_provider.nested1_attr._final_private_  # noqa: B018


@container_context()
async def test_attr_getter_with_invalid_attribute_async(
    some_async_settings_provider: providers.AbstractProvider[Settings],
) -> None:
    with pytest.raises(AttributeError):
        some_async_settings_provider.nested1_attr.nested2_attr.__some_private__  # noqa: B018
    with pytest.raises(AttributeError):
        some_async_settings_provider.nested1_attr.__another_private__  # noqa: B018
    with pytest.raises(AttributeError):
        some_async_settings_provider.nested1_attr._final_private_  # noqa: B018
