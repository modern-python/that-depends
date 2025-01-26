import contextlib
import random
import typing

from fastapi import Depends, FastAPI

from that_depends import BaseContainer, container_context, providers
from that_depends.providers import ContextResource


Scope = typing.MutableMapping[str, typing.Any]
Message = typing.MutableMapping[str, typing.Any]
Receive = typing.Callable[[], typing.Awaitable[Message]]
Send = typing.Callable[[Message], typing.Awaitable[None]]
ASGIApp = typing.Callable[[Scope, Receive, Send], typing.Awaitable[None]]


async def async_resource() -> typing.AsyncIterator[int]:
    """Async resource."""
    yield random.randint(1, 100)  # noqa: S311


def sync_resource_with_args(value: int) -> typing.Iterator[int]:
    """Sync resource."""
    yield value


class MyContainer(BaseContainer):
    """Container."""

    app_provider = providers.Resource(async_resource)
    request_provider = providers.ContextResource(async_resource)
    function_provider = providers.ContextResource(async_resource)
    provider_with_args: ContextResource[int] = providers.ContextResource(sync_resource_with_args, scope=None).with_spec(
        42
    )


@contextlib.asynccontextmanager
async def request_scope() -> typing.AsyncIterator[None]:
    """Enter request scope."""
    async with container_context(MyContainer.request_provider):
        yield


@contextlib.asynccontextmanager
async def function_scope() -> typing.AsyncIterator[None]:
    """Enter function scope."""
    async with container_context(MyContainer.function_provider):
        yield


app = FastAPI()


class MyMiddleware:
    """Middleware."""

    def __init__(
        self,
        app: ASGIApp,
    ) -> None:
        """Init."""
        self.app: typing.Final = app

    async def __call__(self, scope: Scope, receive: Receive, send: Send) -> None:
        """Call."""
        async with request_scope():
            await self.app(scope, receive, send)


app.add_middleware(MyMiddleware)


async def function() -> int:
    """Get random number."""
    return random.randint(1, 100)  # noqa: S311


@app.get("/")
async def root(
    app_variable: typing.Annotated[int, Depends(MyContainer.app_provider)],
    first_request_variable: typing.Annotated[int, Depends(MyContainer.request_provider)],
) -> dict[str, int]:
    """Root."""
    # always enter function scope before calling a function
    # this can also be achieved by wrapping the @inject decorator
    async with function_scope():
        first_function_variable = await function()
    async with function_scope():
        second_function_variable = await function()
    second_request_variable = await MyContainer.request_provider()

    return {
        "app": app_variable,  # same across requests
        "first_request": first_request_variable,
        "second_request": second_request_variable,  # same as value above
        "first_function": first_function_variable,
        "second_function": second_function_variable,
    }


if __name__ == "__main__":
    import uvicorn

    with MyContainer.provider_with_args.sync_context():
        pass

    uvicorn.run(app)
