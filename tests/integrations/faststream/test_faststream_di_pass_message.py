import typing

from faststream import BaseMiddleware, Context, Depends
from faststream.nats import NatsBroker, TestNatsBroker
from faststream.nats.message import NatsMessage
from packaging.version import Version

from that_depends import BaseContainer, container_context, fetch_context_item, providers
from that_depends.integrations.faststream import _FASTSTREAM_VERSION


if Version(_FASTSTREAM_VERSION) >= Version("0.6.0"):  # pragma: no cover
    from faststream.message import StreamMessage
else:  # pragma: no cover
    from faststream.broker.message import StreamMessage  # type: ignore[import-not-found, no-redef]


class ContextMiddleware(BaseMiddleware):
    async def consume_scope(
        self,
        call_next: typing.Callable[..., typing.Awaitable[typing.Any]],
        msg: StreamMessage[typing.Any],
    ) -> typing.Any:  # noqa: ANN401
        async with container_context(global_context={"request": msg}):
            return await call_next(msg)


if Version(_FASTSTREAM_VERSION) >= Version("0.6.0"):  # pragma: no cover
    broker = NatsBroker(middlewares=(ContextMiddleware,))

else:  # pragma: no cover
    broker = NatsBroker(middlewares=(ContextMiddleware,), validate=False)  # type: ignore[call-arg]

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
