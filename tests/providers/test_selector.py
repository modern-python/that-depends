import datetime
import logging
import typing

import pydantic
import pytest

from tests.container import create_async_resource, create_sync_resource
from that_depends import BaseContainer, providers


logger = logging.getLogger(__name__)
global_state_for_selector: typing.Literal["sync_resource", "async_resource", "missing"] = "sync_resource"


class SelectorState:
    def __init__(self) -> None:
        self.selector_state: typing.Literal["sync_resource", "async_resource", "missing"] = "sync_resource"

    def get_selector_state(self) -> typing.Literal["sync_resource", "async_resource", "missing"]:
        return self.selector_state


selector_state = SelectorState()


class DIContainer(BaseContainer):
    alias = "selector_container"
    sync_resource = providers.Resource(create_sync_resource)
    async_resource = providers.Resource(create_async_resource)
    selector: providers.Selector[datetime.datetime] = providers.Selector(
        selector_state.get_selector_state,
        sync_resource=sync_resource,
        async_resource=async_resource,
    )


async def test_selector_provider_async() -> None:
    selector_state.selector_state = "async_resource"
    selected = await DIContainer.selector()
    async_resource = await DIContainer.async_resource()

    assert selected == async_resource


async def test_selector_provider_async_missing() -> None:
    selector_state.selector_state = "missing"
    with pytest.raises(KeyError, match="Key 'missing' not found in providers"):
        await DIContainer.selector()


async def test_selector_provider_sync() -> None:
    selector_state.selector_state = "sync_resource"
    selected = DIContainer.selector.resolve_sync()
    sync_resource = DIContainer.sync_resource.resolve_sync()

    assert selected == sync_resource


async def test_selector_provider_sync_missing() -> None:
    selector_state.selector_state = "missing"
    with pytest.raises(KeyError, match="Key 'missing' not found in providers"):
        DIContainer.selector.resolve_sync()


async def test_selector_provider_overriding() -> None:
    now = datetime.datetime.now(tz=datetime.timezone.utc)
    DIContainer.selector.override_sync(now)
    selected_async = await DIContainer.selector()
    selected_sync = DIContainer.selector.resolve_sync()
    assert selected_async == selected_sync == now

    DIContainer.reset_override_sync()
    selector_state.selector_state = "sync_resource"
    selected = DIContainer.selector.resolve_sync()
    sync_resource = DIContainer.sync_resource.resolve_sync()
    assert selected == sync_resource


class Settings(pydantic.BaseModel):
    mode: typing.Literal["one", "two"] = "one"


class SettingsSelectorContainer(BaseContainer):
    settings = providers.Singleton(Settings)
    operator = providers.Selector(
        settings.cast.mode,
        one=providers.Singleton(lambda: "Provider 1"),
        two=providers.Singleton(lambda: "Provider 2"),
    )


async def test_selector_with_attrgetter_selector_sync() -> None:
    assert SettingsSelectorContainer.settings.resolve_sync().mode == "one"
    assert SettingsSelectorContainer.operator.resolve_sync() == "Provider 1"

    SettingsSelectorContainer.settings.override_sync(Settings(mode="two"))
    assert SettingsSelectorContainer.settings.resolve_sync().mode == "two"
    assert SettingsSelectorContainer.operator.resolve_sync() == "Provider 2"
    SettingsSelectorContainer.settings.reset_override_sync()


async def test_selector_with_attrgetter_selector_async() -> None:
    assert (await SettingsSelectorContainer.settings.resolve()).mode == "one"
    assert (await SettingsSelectorContainer.operator.resolve()) == "Provider 1"

    SettingsSelectorContainer.settings.override_sync(Settings(mode="two"))
    assert (await SettingsSelectorContainer.settings.resolve()).mode == "two"
    assert (await SettingsSelectorContainer.operator.resolve()) == "Provider 2"
    SettingsSelectorContainer.settings.reset_override_sync()


class StringSelectorContainer(BaseContainer):
    selector = providers.Selector(
        "one",
        one=providers.Singleton(lambda: "Provider 1"),
        two=providers.Singleton(lambda: "Provider 2"),
    )


async def test_selector_with_fixed_string() -> None:
    assert StringSelectorContainer.selector.resolve_sync() == "Provider 1"
    assert (await StringSelectorContainer.selector.resolve()) == "Provider 1"


async def mode_one() -> str:
    return "one"


class StringProviderSelectorContainer(BaseContainer):
    mode = providers.AsyncFactory(mode_one)
    selector = providers.Selector(
        mode.cast,
        one=providers.Singleton(lambda: "Provider 1"),
        two=providers.Singleton(lambda: "Provider 2"),
    )


async def test_selector_with_provider_selector_async() -> None:
    assert (await StringProviderSelectorContainer.selector.resolve()) == "Provider 1"


class InvalidSelectorContainer(BaseContainer):
    selector = providers.Selector(
        None,  # type: ignore[arg-type]
        one=providers.Singleton(lambda: "Provider 1"),
        two=providers.Singleton(lambda: "Provider 2"),
    )


async def test_selector_with_invalid_selector() -> None:
    with pytest.raises(
        TypeError, match="Invalid selector type: <class 'NoneType'>, expected str, or a provider/callable returning str"
    ):
        InvalidSelectorContainer.selector.resolve_sync()

    with pytest.raises(
        TypeError, match="Invalid selector type: <class 'NoneType'>, expected str, or a provider/callable returning str"
    ):
        await InvalidSelectorContainer.selector.resolve()
