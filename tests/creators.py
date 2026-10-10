import datetime as dt
import logging
import types
import typing


logger = logging.getLogger(__name__)


async def create_async_resource() -> typing.AsyncIterator[dt.datetime]:
    logger.debug("Async resource initiated")
    try:
        yield dt.datetime.now(tz=dt.timezone.utc)
    finally:
        logger.debug("Async resource destructed")


def create_sync_resource() -> typing.Iterator[dt.datetime]:
    logger.debug("Resource initiated")
    try:
        yield dt.datetime.now(tz=dt.timezone.utc)
    finally:
        logger.debug("Resource destructed")


class ContextManagerResource(typing.ContextManager[dt.datetime]):
    def __enter__(self) -> dt.datetime:
        logger.debug("Resource initiated")
        return dt.datetime.now(tz=dt.timezone.utc)

    def __exit__(
        self,
        exc_type: type[BaseException] | None,
        exc_value: BaseException | None,
        traceback: types.TracebackType | None,
    ) -> None:
        logger.debug("Resource destructed")


class AsyncContextManagerResource(typing.AsyncContextManager[dt.datetime]):
    async def __aenter__(self) -> dt.datetime:
        logger.debug("Async resource initiated")
        return dt.datetime.now(tz=dt.timezone.utc)

    async def __aexit__(
        self,
        exc_type: type[BaseException] | None,
        exc_value: BaseException | None,
        traceback: types.TracebackType | None,
    ) -> None:
        logger.debug("Async resource destructed")
