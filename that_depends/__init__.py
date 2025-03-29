"""Dependency injection framework for Python."""

from that_depends import providers
from that_depends.container import BaseContainer
from that_depends.injection import Provide, inject
from that_depends.providers import container_context
from that_depends.providers.context_resources import (
    ContextScope,
    ContextScopes,
    fetch_context_item,
    fetch_context_item_by_type,
    get_current_scope,
)


__all__ = [
    "BaseContainer",
    "ContextScope",
    "ContextScopes",
    "Provide",
    "container_context",
    "fetch_context_item",
    "fetch_context_item_by_type",
    "get_current_scope",
    "inject",
    "providers",
]
