import typing

from faststream import BaseMiddleware, Context, Depends
from faststream.broker.message import StreamMessage
from faststream.nats import NatsBroker, TestNatsBroker
from faststream.nats.message import NatsMessage

from that_depends import BaseContainer, container_context, fetch_context_item, providers


class ContextMiddleware(BaseMiddleware):
    async def consume_scope(
        self,
        call_next: typing.Callable[..., typing.Awaitable[typing.Any]],
        msg: StreamMessage[typing.Any],
    ) -> typing.Any:  # noqa: ANN401
        async with container_context(global_context={"request": msg}):
            return await call_next(msg)


broker = NatsBroker(middlewares=(ContextMiddleware,), validate=False)

TEST_SUBJECT = "test"


class DIContainer(BaseContainer):
    context_request = providers.Factory(
        lambda: fetch_context_item("request"),
    )


@broker.subscriber(TEST_SUBJECT)
async def index_subscriber(
    context_request: typing.Annotated[
        NatsMessage,
        Depends(DIContainer.context_request, cast=False),
    ],
    message: typing.Annotated[
        NatsMessage,
        Context(),
    ],
) -> bool:
    return message is context_request


async def test_read_main() -> None:
    async with TestNatsBroker(broker) as br:
        result = await br.request(None, TEST_SUBJECT)

        assert (await result.decode()) is True
