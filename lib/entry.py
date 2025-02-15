from datetime import datetime

from lib.di import Container
from that_depends import Provide, container_context, inject


@Container.context_resource.context
def entry_point_with_wrapper() -> None:
    library_code_with_context_resource()


def entry_point_with_explicit() -> None:
    with Container.context_resource.sync_context():
        library_code_with_context_resource()


@container_context(Container.context_resource, Container.another_context_resource)  # make sure `that-depends>=2.1.1`
def entry_with_multiple_resources_wrapped() -> None:
    library_code_with_context_resource()


def entry_with_multiple_resources_explicit() -> None:
    with container_context(Container.context_resource, Container.another_context_resource):
        # this will only call initialization and finalization of `another_context_resource` if it actually
        # gets used in the rest of the code
        library_code_with_context_resource()


def entry_point_with_resource() -> None:
    library_code_with_resource()
    Container.resource.sync_tear_down()


@inject
def library_code_with_context_resource(time: datetime = Provide[Container.context_resource]) -> None:
    pass


@inject
def library_code_with_resource(time: datetime = Provide[Container.resource]) -> None:
    pass
