from __future__ import annotations
import typing

import pytest

from that_depends import BaseContainer, Provide, providers


if typing.TYPE_CHECKING:

    class Unresolvable:
        pass


class Service:
    pass


class FutureAnnotationsContainer(BaseContainer):
    service = providers.Object(Service()).bind(Service)


@FutureAnnotationsContainer.inject
def inject_service_sync(service: Service = Provide()) -> Service:
    return service


@FutureAnnotationsContainer.inject
async def inject_service_async(service: Service = Provide()) -> Service:
    return service


def test_type_based_injection_resolves_postponed_annotations_sync() -> None:
    assert isinstance(inject_service_sync(), Service)


async def test_type_based_injection_resolves_postponed_annotations_async() -> None:
    assert isinstance(await inject_service_async(), Service)


def test_type_based_injection_rejects_unresolvable_local_annotation() -> None:
    class LocalService:
        pass

    with pytest.raises(TypeError, match="Cannot resolve annotations for injected function"):

        @FutureAnnotationsContainer.inject
        def target(service: LocalService = Provide()) -> LocalService:  # pragma: no cover
            return service


def test_type_based_injection_rejects_non_concrete_annotation() -> None:
    with pytest.raises(TypeError, match="Type-based injection for 'service' requires a concrete runtime type"):

        @FutureAnnotationsContainer.inject
        def target(service: list[str] = Provide()) -> list[str]:  # pragma: no cover
            return service


def test_direct_provider_injection_does_not_resolve_unrelated_annotations() -> None:
    provider = providers.Object(1)

    @FutureAnnotationsContainer.inject
    def target(value: int = Provide[provider], unrelated: Unresolvable | None = None) -> int:
        _ = unrelated
        return value

    assert target() == 1
