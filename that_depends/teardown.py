import typing

from that_depends.providers.attr_getter import AttrGetter
from that_depends.providers.base import AbstractProvider, AbstractResource
from that_depends.providers.singleton import Singleton


async def tear_down(providers: typing.Iterable[AbstractProvider[typing.Any]]) -> None:
    dependents_by_provider: dict[AbstractProvider[typing.Any], set[AbstractProvider[typing.Any]]] = {}
    for provider in providers:
        dependents_by_provider.setdefault(provider, set())
        for dependency in provider.dependencies:
            if isinstance(dependency, AttrGetter):
                dependents_by_provider.setdefault(dependency.provider, set())
                dependents_by_provider[dependency.provider].add(dependency)
            dependents_by_provider.setdefault(dependency, set())
            dependents_by_provider[dependency].add(provider)
    await _tear_down_in_dependency_order(dependents_by_provider)


async def _tear_down_in_dependency_order(
    dependents_by_provider: dict[AbstractProvider[typing.Any], set[AbstractProvider[typing.Any]]],
) -> None:
    while dependents_by_provider:
        torn_down = []
        for provider, dependents in dependents_by_provider.items():
            if not dependents:
                # There are no other providers that depend on the provider
                if isinstance(provider, AbstractResource | Singleton):
                    await provider.tear_down()
                for dependency in provider.dependencies:
                    dependents_by_provider[dependency].discard(provider)
                torn_down.append(provider)
        for provider in torn_down:
            dependents_by_provider.pop(provider)
