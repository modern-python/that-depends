from that_depends.providers.base import AbstractProvider, AbstractResource
from that_depends.providers.collections import List
from that_depends.providers.factories import AsyncFactory, Factory
from that_depends.providers.resources import AsyncResource, Resource


__all__ = [
    "AbstractProvider",
    "AbstractResource",
    "Resource",
    "AsyncResource",
    "Factory",
    "AsyncFactory",
    "List",
    "Singleton",
]

from that_depends.providers.singleton import Singleton
