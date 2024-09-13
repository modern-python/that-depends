import datetime
import logging
import typing

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
    with pytest.raises(RuntimeError, match="No provider matches"):
        await DIContainer.selector()


async def test_selector_provider_sync() -> None:
    selector_state.selector_state = "sync_resource"
    selected = DIContainer.selector.sync_resolve()
    sync_resource = DIContainer.sync_resource.sync_resolve()

    assert selected == sync_resource


async def test_selector_provider_sync_missing() -> None:
    selector_state.selector_state = "missing"
    with pytest.raises(RuntimeError, match="No provider matches"):
        DIContainer.selector.sync_resolve()


async def test_selector_provider_overriding() -> None:
    now = datetime.datetime.now(tz=datetime.timezone.utc)
    DIContainer.selector.override(now)
    selected_async = await DIContainer.selector()
    selected_sync = DIContainer.selector.sync_resolve()
    assert selected_async == selected_sync == now

    DIContainer.reset_override()
    selector_state.selector_state = "sync_resource"
    selected = DIContainer.selector.sync_resolve()
    sync_resource = DIContainer.sync_resource.sync_resolve()
    assert selected == sync_resource
