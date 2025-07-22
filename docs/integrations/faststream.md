# Usage with `FastStream`


`that-depends` is out of the box compatible with `faststream.Depends()`:

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


## Context Middleware

If you are using [ContextResource](../providers/context-resources.md) provider, you likely will want to
initialize a context before processing message with `faststream.`

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
