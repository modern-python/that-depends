import random
import typing
from http import HTTPStatus
from inspect import signature
from typing import get_type_hints

from fastapi import APIRouter, Depends, FastAPI
from fastapi.testclient import TestClient

from that_depends import BaseContainer, Provide, providers
from that_depends.integrations.fastapi import _adjust_fastapi_endpoint, create_fastapi_route_class
from that_depends.providers.context_resources import ContextScopes


_FACTORY_RETURN_VALUE = 42


async def _async_creator() -> typing.AsyncIterator[float]:
    yield random.random()


def _sync_creator() -> typing.Iterator[float]:
    yield random.random()


class Container(BaseContainer):
    alias = "fastapi_route_class_container"
    provider = providers.Factory(lambda: _FACTORY_RETURN_VALUE)
    async_context_provider = providers.ContextResource(_async_creator).with_config(scope=ContextScopes.REQUEST)
    sync_context_provider = providers.ContextResource(_sync_creator).with_config(scope=ContextScopes.REQUEST)


async def test_endpoint_with_context_resource_async() -> None:
    app = FastAPI()

    router = APIRouter(route_class=create_fastapi_route_class(Container, scope=ContextScopes.REQUEST))

    @router.get("/hello")
    async def _injected(v_3: float = Provide[Container.async_context_provider]) -> float:
        return v_3

    app.include_router(router)

    client = TestClient(app)

    response = client.get("/hello")

    response_value = response.json()

    assert response.status_code == HTTPStatus.OK
    assert response_value <= 1
    assert response_value >= 0

    assert response_value != client.get("/hello").json()


def test_endpoint_with_context_resource_sync() -> None:
    app = FastAPI()

    router = APIRouter(route_class=create_fastapi_route_class(Container, scope=ContextScopes.REQUEST))

    @router.get("/hello")
    def _injected(v_3: float = Provide[Container.sync_context_provider]) -> float:
        return v_3

    app.include_router(router)

    client = TestClient(app)

    response = client.get("/hello")

    response_value = response.json()

    assert response.status_code == HTTPStatus.OK
    assert response_value <= 1
    assert response_value >= 0

    assert response_value != client.get("/hello").json()


async def test_endpoint_factory_async() -> None:
    app = FastAPI()

    router = APIRouter(route_class=create_fastapi_route_class(Container, scope=ContextScopes.REQUEST))

    @router.get("/hello")
    async def _injected(v_3: float = Provide[Container.provider]) -> float:
        return v_3

    app.include_router(router)

    client = TestClient(app)

    response = client.get("/hello")

    response_value = response.json()

    assert response.status_code == HTTPStatus.OK
    assert response_value == _FACTORY_RETURN_VALUE

    assert response_value == client.get("/hello").json()


def test_endpoint_factory_sync() -> None:
    app = FastAPI()

    router = APIRouter(route_class=create_fastapi_route_class(Container, scope=ContextScopes.REQUEST))

    @router.get("/hello")
    def _injected(v_3: float = Provide[Container.provider]) -> float:
        return v_3

    app.include_router(router)

    client = TestClient(app)

    response = client.get("/hello")

    response_value = response.json()

    assert response.status_code == HTTPStatus.OK
    assert response_value == _FACTORY_RETURN_VALUE

    assert response_value == client.get("/hello").json()


async def test_endpoint_with_string_provider_async() -> None:
    app = FastAPI()

    router = APIRouter(route_class=create_fastapi_route_class(Container, scope=ContextScopes.REQUEST))

    @router.get("/hello")
    async def _injected(v_3: float = Provide["fastapi_route_class_container.provider"]) -> float:
        return v_3

    app.include_router(router)

    client = TestClient(app)

    response = client.get("/hello")

    response_value = response.json()

    assert response.status_code == HTTPStatus.OK
    assert response_value == _FACTORY_RETURN_VALUE

    assert response_value == client.get("/hello").json()


async def test_endpoint_with_string_provider_sync() -> None:
    app = FastAPI()

    router = APIRouter(route_class=create_fastapi_route_class(Container, scope=ContextScopes.REQUEST))

    @router.get("/hello")
    def _injected(v_3: float = Provide["fastapi_route_class_container.provider"]) -> float:
        return v_3

    app.include_router(router)

    client = TestClient(app)

    response = client.get("/hello")

    response_value = response.json()

    assert response.status_code == HTTPStatus.OK
    assert response_value == _FACTORY_RETURN_VALUE

    assert response_value == client.get("/hello").json()


def test_adjust_fastapi_endpoint_async() -> None:
    async def _injected(
        v_1: float,
        v_3: float = Provide["fastapi_route_class_container.provider"],
        v_2: float = Depends(Container.provider),
    ) -> float:
        return v_1 + v_3 + v_2  # pragma: no cover

    original_signature = signature(_injected)
    original_hints = get_type_hints(_injected)

    adjusted_endpoint = _adjust_fastapi_endpoint(_injected)

    adjusted_sig = signature(adjusted_endpoint)
    adjusted_hints = get_type_hints(adjusted_endpoint)

    assert len(original_hints) == len(adjusted_hints)
    assert len(original_signature.parameters) == len(adjusted_sig.parameters)
    assert original_hints.get("v_1") == adjusted_hints.get("v_1")
    assert original_hints.get("v_2") == adjusted_hints.get("v_2")
    assert original_hints.get("v_3") != adjusted_hints.get("v_3")
    assert original_signature.parameters.get("v_1") == adjusted_sig.parameters.get("v_1")
    assert original_signature.parameters.get("v_2") == adjusted_sig.parameters.get("v_2")
    assert original_signature.parameters.get("v_3") != adjusted_sig.parameters.get("v_3")


def test_adjust_fastapi_endpoint_sync() -> None:
    def _injected(
        v_1: float,
        v_3: float = Provide["fastapi_route_class_container.provider"],
        v_2: float = Depends(Container.provider),
    ) -> float:
        return v_1 + v_3 + v_2  # pragma: no cover

    original_signature = signature(_injected)
    original_hints = get_type_hints(_injected)

    adjusted_endpoint = _adjust_fastapi_endpoint(_injected)

    adjusted_sig = signature(adjusted_endpoint)
    adjusted_hints = get_type_hints(adjusted_endpoint)

    assert len(original_hints) == len(adjusted_hints)
    assert len(original_signature.parameters) == len(adjusted_sig.parameters)
    assert original_hints.get("v_1") == adjusted_hints.get("v_1")
    assert original_hints.get("v_2") == adjusted_hints.get("v_2")
    assert original_hints.get("v_3") != adjusted_hints.get("v_3")
    assert original_signature.parameters.get("v_1") == adjusted_sig.parameters.get("v_1")
    assert original_signature.parameters.get("v_2") == adjusted_sig.parameters.get("v_2")
    assert original_signature.parameters.get("v_3") != adjusted_sig.parameters.get("v_3")
