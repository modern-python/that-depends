import datetime
import logging
import types
import typing


logger = logging.getLogger(__name__)


async def create_async_resource() -> typing.AsyncIterator[datetime.datetime]:
    logger.debug("Async resource initiated")
    try:
        yield datetime.datetime.now(tz=datetime.timezone.utc)
    finally:
        logger.debug("Async resource destructed")


def create_sync_resource() -> typing.Iterator[datetime.datetime]:
    logger.debug("Resource initiated")
    try:
        yield datetime.datetime.now(tz=datetime.timezone.utc)
    finally:
        logger.debug("Resource destructed")


class ContextManagerResource(typing.ContextManager[datetime.datetime]):
    def __enter__(self) -> datetime.datetime:
        logger.debug("Resource initiated")
        return datetime.datetime.now(tz=datetime.timezone.utc)

    def __exit__(
        self,
        exc_type: type[BaseException] | None,
        exc_value: BaseException | None,
        traceback: types.TracebackType | None,
    ) -> None:
        logger.debug("Resource destructed")


class AsyncContextManagerResource(typing.AsyncContextManager[datetime.datetime]):
    async def __aenter__(self) -> datetime.datetime:
        logger.debug("Async resource initiated")
        return datetime.datetime.now(tz=datetime.timezone.utc)

    async def __aexit__(
        self,
        exc_type: type[BaseException] | None,
        exc_value: BaseException | None,
        traceback: types.TracebackType | None,
    ) -> None:
        logger.debug("Async resource destructed")
