# Usage with FastAPI

!!! info "See also"
    [`modern-di-fastapi`](https://github.com/modern-python/modern-di-fastapi) is the equivalent
    FastAPI integration for [`modern-di`](https://github.com/modern-python/modern-di), the newer
    sibling DI framework.

## Installation

To use `that-depends` with FastAPI, you need to install the package with the `fastapi` extra. You can do this using pip:

```bash
pip install that-depends[fastapi]
```

---

## Creating a container

Suppose you have a simple container in a file called `mycontainer.py`:

```python
# mycontainer.py
import datetime

from that_depends import BaseContainer, providers

def create_time() -> datetime.datetime:
    """Example sync resource creator."""
    return datetime.datetime.now()

class MyContainer(BaseContainer):
    # A simple provider that always returns a "datetime.datetime" object
    current_time = providers.Factory(create_time)
```

Here, `MyContainer.current_time` is a provider that, when called, creates a new `datetime.datetime` using `create_time()`.

---

## Using a custom router class

You can use the `create_fastapi_route_class()` method to create a custom route class for your application:

```python
from that_depends.integrations.fastapi import create_fastapi_route_class

my_route_class = create_fastapi_route_class()
```

You can then use this class in your `FastAPI` router:
```python

from fastapi import APIRouter

router = APIRouter(route_class=my_route_class)
```

This will enable you to use dependency injection in your `FastAPI` endpoints:

> If you don't want to use the custom router class, you can use `fastapi.Depends` instead.


=== "Router class"
    ```python
    from that_depends import Provide
    
    @router.get("/time")
    async def get_time(current_time: datetime.datetime = Provide[MyContainer.current_time]) -> datetime.datetime:
        return current_time
    ```

=== "Router class with string provider"
    ```python
    from that_depends import Provide
    
    @router.get("/time")
    async def get_time(current_time: datetime.datetime = Provide["MyContainer.current_time"]) -> datetime.datetime:
        return current_time
    ```

=== "Using fastapi.Depends"
    ```python
    from fastapi import Depends
    
    @router.get("/time")
    async def get_time(current_time: datetime.datetime = Depends(MyContainer.current_time)) -> datetime.datetime:
        return current_time
    ```

### Managing container context

To initialize the container context, pass arguments to `create_fastapi_route_class()`:

```python
from that_depends import ContextScopes

my_route_class = create_fastapi_route_class(MyContainer, global_context={"key": "value"}, scope=ContextScopes.REQUEST)
```

In the above example, all `ContextResources` in our container that are `REQUEST` scoped will be initialized
and the global context will be set.



## Integrating with FastAPI using DIContextMiddleware

The `DIContextMiddleware` can be used to manage context, but its features overlap with the [custom router class](#using-a-custom-router-class).
The main advantage of using middleware is that you can set it up for your entire `FastAPI` application.

> If you want to use both the `DIContextMiddleware` and the custom router class, do not pass any arguments to `create_fastapi_route_class()`.

### Setting up the FastAPI app

You can use the `DIContextMiddleware` from `that-depends` so that any request automatically initializes the context for your container(s). This approach is convenient if you want to:

- Automatically initialize or tear down resources on each request.
- Provide a global or request-level context dictionary you can read from your container.

A minimal example in `main.py`:

```python
# main.py
from fastapi import FastAPI, Depends
from starlette.responses import Response
from that_depends.providers import DIContextMiddleware

from mycontainer import MyContainer

app = FastAPI()

# Attach the middleware, optionally passing the container and/or a global_context
app.add_middleware(
    DIContextMiddleware,
    MyContainer,
    global_context={"app_name": "MyApp"},  # optional dictionary available in the context
)

@app.get("/")
def get_time(
    # Using container's provider as a dependency:
    current_time: str = Depends(MyContainer.current_time)
) -> Response:
    return Response(
        content=f"Current time is: {current_time}",
        media_type="text/plain",
    )
```

- `DIContextMiddleware` automatically sets a global context for every request.
- The `Depends(MyContainer.current_time)` call is how you reference the container’s provider using the standard FastAPI injection system.

To run this app:

```bash
uvicorn main:app --reload
```

When you make a request to `/`, you will see the current time printed, and behind the scenes the that-depends container is in a context.

> If your container uses context-based resources such as `ContextResource`, you can also set `default_scope` in your container or configure an explicit scope. See the advanced section below.

---



## Examples of different providers in FastAPI

### Singleton providers

```python
# Suppose in mycontainer.py

from that_depends import BaseContainer, providers
from pydantic import BaseModel

class AppSettings(BaseModel):
    database_url: str = "sqlite:///:memory:"

class MyAdvancedContainer(BaseContainer):
    # Provide a single, shared settings instance
    settings = providers.Singleton(AppSettings)
```

In your route:

```python
from fastapi import FastAPI, Depends
from mycontainer import MyAdvancedContainer

app = FastAPI()

@app.get("/settings")
def read_settings(settings: AppSettings = Depends(MyAdvancedContainer.settings)):
    return {"db_url": settings.database_url}
```

### Context resources

For “request-scoped” resources (e.g. a DB connection per request), you can use `ContextResource` in your container. This typically works in conjunction with `DIContextMiddleware` or a manual `container_context(...)` call. For example:

```python
# Suppose in mycontainer.py
import typing
from that_depends import BaseContainer, providers
from that_depends.providers.context_resources import ContextScopes

async def db_session_creator() -> typing.AsyncIterator[str]:
    print("Opening DB connection")
    yield "fake_db_session"
    print("Closing DB connection")

class MyScopedContainer(BaseContainer):
    # Tells that-depends that each resource has a context scope (like "request").
    default_scope = ContextScopes.REQUEST

    db_session = providers.ContextResource(db_session_creator)
```

Then in your FastAPI app:

```python
# main.py
from fastapi import FastAPI, Depends
from that_depends.providers.context_resources import ContextScopes, DIContextMiddleware
from mycontainer import MyScopedContainer

app = FastAPI()
app.add_middleware(
    DIContextMiddleware,
    MyScopedContainer,
    scope=ContextScopes.REQUEST,
)

@app.get("/")
async def read_db(
    session: str = Depends(MyScopedContainer.db_session)
):
    return {"session": session}
```

- Because `MyScopedContainer.default_scope == ContextScopes.REQUEST`, each incoming request initializes a new DB session and tears it down automatically once the request completes (thanks to `DIContextMiddleware`).

---

## Testing with FastAPI

When writing unit tests, you can use `TestClient` from `starlette.testclient` or `pytest-asyncio` with standard FastAPI patterns. The `DIContextMiddleware` approach ensures resources are created and torn down automatically each request, so no special arrangement is necessary.

For example:

```python
import pytest
from starlette.testclient import TestClient

from main import app  # The FastAPI app

@pytest.fixture
def client() -> TestClient:
    return TestClient(app)

def test_read_db(client: TestClient):
    response = client.get("/")
    assert response.status_code == 200
    data = response.json()
    assert data["session"] == "fake_db_session"
```

---

## Common patterns and tips

- Decide whether your container's dependencies should be globally shared (e.g., singletons) or created anew per request (e.g., database or session).
- You can generally pass `Depends(MyContainer.some_provider)` to route handlers, and `that-depends` resolves the provider under the hood.
- You can override a provider in tests by calling `MyContainer.some_provider.override_sync(...)` or using the context manager `with MyContainer.some_provider.override_context_sync(...):`.
- If you have expensive creation logic (like a DB engine that can be reused globally), prefer a `Singleton` or `Object` provider. If you need ephemeral resources, use `ContextResource` with the `DIContextMiddleware`.
- If you do not want to rely on the middleware, you can create a context manually in any async function by calling `async with container_context(MyContainer):`.
- You can define multiple containers and connect them (e.g., `ContainerA.connect_containers(ContainerB)`), or add them all to the `DIContextMiddleware`. See [Usage with multiple containers](../introduction/multiple-containers.md) for details.


### Accessing the FastAPI request or other context items

Sometimes you want to pass the `fastapi.Request` (or other request-scoped data) into the container context so that providers can read it. You can do that either via the `DIContextMiddleware` (by customizing the `global_context` dynamically) or by writing your own dependency that calls `container_context()`.

For example, a custom dependency that sets up the context with the current `Request`:

```python
# request_deps.py
from fastapi import Request
from typing import AsyncIterator
from that_depends import container_context

async def init_di_context(request: Request) -> AsyncIterator[None]:
    # We store the request in a that_depends global context
    async with container_context(global_context={"request": request}):
        yield
```

Then in your `FastAPI` route:

```python
# main.py (extended)
from fastapi import FastAPI, Request, Depends
from starlette.responses import JSONResponse
from that_depends import fetch_context_item

from request_deps import init_di_context
from mycontainer import MyContainer

app = FastAPI()

# Notice no DIContextMiddleware here, but you could combine them
@app.get("/request-based", dependencies=[Depends(init_di_context)])
async def get_request_info(
    # This provider fetches the request from context:
    request_in_container: Request = Depends(MyContainer.resolver(lambda: fetch_context_item("request"))),
):
    # The provider can read from that-depends context. We used .resolver(...) here as an example,
    # but you can define a dedicated provider in MyContainer that returns fetch_context_item("request").
    return JSONResponse({"request_url": str(request_in_container.url)})
```

Now each request calls `init_di_context(...)`, sets the request object into the global context, and any provider that reads from `"request"` can retrieve it.

---
