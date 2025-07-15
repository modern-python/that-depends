"""Providers."""

from that_depends.providers.base import AbstractProvider, AttrGetter
from that_depends.providers.collection import Dict, List
from that_depends.providers.context_resources import (
    ContextResource,
    DIContextMiddleware,
    container_context,
)
from that_depends.providers.factories import AsyncFactory, Factory
from that_depends.providers.local_singleton import ThreadLocalSingleton
from that_depends.providers.object import Object
from that_depends.providers.resources import Resource
from that_depends.providers.selector import Selector
from that_depends.providers.singleton import AsyncSingleton, Singleton
from that_depends.providers.state import State


__all__ = [
    "AbstractProvider",
    "AsyncFactory",
    "AsyncSingleton",
    "AttrGetter",
    "ContextResource",
    "DIContextMiddleware",
    "Dict",
    "Factory",
    "List",
    "Object",
    "Resource",
    "Selector",
    "Singleton",
    "State",
    "ThreadLocalSingleton",
    "container_context",
]
