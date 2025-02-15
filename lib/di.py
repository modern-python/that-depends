import typing
from datetime import datetime

from that_depends import BaseContainer, providers


def create_sync_resource() -> typing.Iterator[datetime]:
    yield datetime.now()


class Container(BaseContainer):
    """Container for the application."""

    default_scope = None

    context_resource = providers.ContextResource(create_sync_resource)
    another_context_resource = providers.ContextResource(create_sync_resource)
    resource = providers.Resource(create_sync_resource)
