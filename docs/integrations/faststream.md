# Usage with `FastStream`

!!! info "See also"
    [`modern-di-faststream`](https://github.com/modern-python/modern-di-faststream) is the
    equivalent FastStream integration for [`modern-di`](https://github.com/modern-python/modern-di),
    the newer sibling DI framework.

`that-depends` works out of the box with `faststream.Depends()`:

```python hl_lines="14"
from typing import Annotated
from faststream import Depends
from faststream.asgi import AsgiFastStream
from faststream.rabbit import  RabbitBroker


broker = RabbitBroker()
app = AsgiFastStream(broker)

@broker.subscriber(queue="queue")
async def process(
    text: str,
    suffix: Annotated[
        str, Depends(Container.suffix_factory) # (1)!
    ],
) -> None:    
    return text + suffix
```

1. This would be the same as `Provide[Container.suffix_factory]`


## Context middleware

If you are using [ContextResource](../providers/context-resources.md) provider, you will likely want to
initialize a context before processing messages with `faststream.`

`that-depends` provides integration for these use cases:

```shell
pip install that-depends[faststream]
```

Then you can use the `DIContextMiddleware` with your broker:

```python
from that_depends.integrations.faststream import DIContextMiddleware
from that_depends import ContextScopes
from faststream.rabbit import  RabbitBroker

broker = RabbitBroker(middlewares=[DIContextMiddleware(Container, scope=ContextScopes.REQUEST)])
```

## Example

Here is an example that includes life-cycle events:

```python
import contextlib
import dataclasses
import datetime
import typing

from faststream import FastStream, Depends, Logger
from faststream.rabbit import RabbitBroker

from that_depends import BaseContainer, providers


async def create_async_resource() -> typing.AsyncIterator[datetime.datetime]:
    yield datetime.datetime.now(tz=datetime.timezone.utc)


@dataclasses.dataclass(kw_only=True, slots=True)
class DependentFactory:
    async_resource: datetime.datetime


class DIContainer(BaseContainer):
    async_resource = providers.Resource(create_async_resource)
    dependent_factory = providers.Factory(DependentFactory, async_resource=async_resource.cast)


@contextlib.asynccontextmanager
async def lifespan_manager() -> typing.AsyncIterator[None]:
    try:
        yield
    finally:
        await DIContainer.tear_down()


broker = RabbitBroker()
app = FastStream(broker, lifespan=lifespan_manager)


@broker.subscriber("in")
async def read_root(
    logger: Logger,
    some_dependency: typing.Annotated[
        DependentFactory,
        Depends(DIContainer.dependent_factory)
    ],
) -> datetime.datetime:
    startup_time = some_dependency.async_resource
    logger.info(startup_time)
    return startup_time


@app.after_startup
async def t() -> None:
    await broker.publish(None, "in")
```
