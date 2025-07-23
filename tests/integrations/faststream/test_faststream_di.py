import datetime
import typing

from faststream import Depends
from faststream.nats import NatsBroker, TestNatsBroker

from tests import container
from that_depends.integrations.faststream import DIContextMiddleware


broker = NatsBroker(middlewares=[DIContextMiddleware(container.DIContainer.context_resource)])

TEST_SUBJECT = "test"


@broker.subscriber(TEST_SUBJECT)
async def index_subscriber(
    dependency: typing.Annotated[
        container.DependentFactory,
        Depends(container.DIContainer.dependent_factory),
    ],
    free_dependency: typing.Annotated[
        container.FreeFactory,
        Depends(container.DIContainer.resolver(container.FreeFactory)),
    ],
    singleton: typing.Annotated[
        container.SingletonFactory,
        Depends(container.DIContainer.singleton),
    ],
    singleton_attribute: typing.Annotated[bool, Depends(container.DIContainer.singleton.dep1)],
    context_resource: typing.Annotated[datetime.datetime, Depends(container.DIContainer.context_resource)],
) -> datetime.datetime:
    assert dependency.sync_resource == free_dependency.dependent_factory.sync_resource
    assert dependency.async_resource == free_dependency.dependent_factory.async_resource
    assert singleton.dep1 is True
    assert singleton_attribute is True
    assert isinstance(context_resource, datetime.datetime)
    return dependency.async_resource


async def test_read_main() -> None:
    async with TestNatsBroker(broker) as br:
        result = await br.request(None, TEST_SUBJECT)

        result_str = typing.cast(str, await result.decode())
        assert (
            datetime.datetime.fromisoformat(result_str.replace("Z", "+00:00"))
            == await container.DIContainer.async_resource()
        )
