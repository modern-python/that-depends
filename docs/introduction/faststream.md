# Usage with `FastStream`

```python
import datetime
import contextlib
import typing

from faststream import FastStream, Depends, Logger
from faststream.rabbit import RabbitBroker

from tests import container


@contextlib.asynccontextmanager
async def lifespan_manager() -> typing.AsyncIterator[None]:
    try:
        yield
    finally:
        await container.DIContainer.tear_down()


broker = RabbitBroker()
app = FastStream(broker, lifespan=lifespan_manager)


@broker.subscriber("in")
async def read_root(
    logger: Logger,
    some_dependency: typing.Annotated[
        container.DependentFactory,
        Depends(container.DIContainer.dependent_factory)
    ],
) -> datetime.datetime:
    startup_time = some_dependency.async_resource
    logger.info(startup_time)
    return startup_time


@app.after_startup
async def t() -> None:
    await broker.publish(None, "in")
```
