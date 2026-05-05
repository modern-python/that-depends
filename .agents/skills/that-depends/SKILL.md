---
name: that-depends
description: Guide for using the `that-depends` library, a Python dependency injection framework.
---

# `that-depends`

`that-depends` is a typed dependency-injection framework for Python. The core workflow is:

1. Define a `BaseContainer`.
2. Register providers as class attributes.
3. Consume dependencies with `@inject` and `Provide[...]`.
4. Use context decorators for `ContextResource` providers.
5. Override providers in tests instead of patching call sites.

## Recommended usage

### Define providers on a container

Keep providers on `BaseContainer` subclasses instead of as standalone globals, especially if you need context features.

```python
from that_depends import BaseContainer, providers


class Settings:
    def __init__(self) -> None:
        self.base_url = "https://api.example.com"


class ApiClient:
    def __init__(self, base_url: str) -> None:
        self.base_url = base_url


class UserService:
    def __init__(self, client: ApiClient) -> None:
        self.client = client


class Container(BaseContainer):
    settings = providers.Singleton(Settings)
    api_client = providers.Factory(ApiClient, base_url=settings.cast.base_url)
    user_service = providers.Factory(UserService, client=api_client.cast)
```

### Prefer the decorator API for application code

Use `@inject` with `Provide[Container.provider]` defaults.

```python
from that_depends import Provide, inject


@inject
def handle_user(service: UserService = Provide[Container.user_service]) -> UserService:
    return service

```

This is the preferred style over explicit `resolve()` / `resolve_sync()` calls in application code.

## Provider cheat sheet

| Provider | Use for |
| --- | --- |
| `Singleton` / `AsyncSingleton` | One cached instance |
| `Factory` / `AsyncFactory` | New value on each resolution |
| `Resource` | Cached value with teardown |
| `ContextResource` | Per-context / per-scope resource |
| `Sequence` / `Mapping` | Aggregate multiple providers into read-only collection types |
| `Selector` | Choose one provider from a key |
| `State` | Pass runtime state through context |

## Best practices

### Prefer injection over explicit resolution

Avoid calling `resolve()` and `resolve_sync()` inside normal application code. Inject dependencies into function parameters instead.
Reserve explicit resolution for bootstrapping, one-off scripts, REPL usage, or tests.

**Avoid:**

```python
def create_handler() -> UserService:
    return Container.user_service.resolve_sync()
```

**Prefer:**

```python
@inject
def create_handler(service: UserService = Provide[Container.user_service]) -> UserService:
    return service
```

Why this is better:

- it keeps call sites easy to override in tests;
- it works naturally with scoped/context-managed providers;
- callers can still pass explicit arguments without overriding providers.

### Do not call `resolve()` / `resolve_sync()` in injected function bodies

This is especially important for `ContextResource` providers. The injection system initializes context for dependencies declared in `Provide[...]` defaults; explicit resolution inside the function body is discouraged and can fail for scoped resources.

**Avoid:**

```python
import typing

from that_depends.providers.context_resources import ContextScopes


def open_session() -> typing.Iterator[str]:
    yield "session"


class Container(BaseContainer):
    default_scope = ContextScopes.INJECT
    session = providers.ContextResource(open_session).with_config(scope=ContextScopes.INJECT)


@inject(scope=ContextScopes.INJECT)
def bad() -> str:
    return Container.session.resolve_sync()
```

**Prefer:**

```python
@inject(scope=ContextScopes.INJECT)
def good(session: str = Provide[Container.session]) -> str:
    return session
```

### Prefer `provider.context()` over `container_context()`

If you only need to initialize context for one provider, prefer the provider decorator/context API. It is more local and easier to read.

**Preferred for a single provider:**

```python
import typing

from that_depends import Provide, inject


def request_id_resource() -> typing.Iterator[str]:
    yield "req-123"


class Container(BaseContainer):
    request_id = providers.ContextResource(request_id_resource)


@Container.request_id.context
@inject
def endpoint(request_id: str = Provide[Container.request_id]) -> str:
    return request_id
```

Use `container_context()` when you need one of these:

- initialize context for multiple providers or containers at once;
- pass `global_context`;
- manually control a named scope.

```python
from that_depends import container_context
from that_depends.providers.context_resources import ContextScopes


async with container_context(
    Container.request_id,
    global_context={"trace_id": "abc-123"},
    scope=ContextScopes.REQUEST,
):
    ...
```

If you need all `ContextResource` providers in one container, `@Container.context` is often cleaner than `container_context(Container)`.

```python
@Container.context
@inject
async def run_endpoint(request_id: str = Provide[Container.request_id]) -> str:
    return request_id
```

### Prefer direct provider references

Use `Provide[Container.provider]` directly in examples and normal application code:

```python
@inject
def fn(service: UserService = Provide[Container.user_service]) -> UserService:
    return service
```

### Use overrides in tests

Prefer provider or container override APIs over patching internals.

```python
def test_handler_override() -> None:
    fake_service = UserService(ApiClient("https://test.example.com"))

    with Container.user_service.override_context_sync(fake_service):
        assert create_handler() is fake_service
```

If you override an upstream cached dependency and need dependents to refresh, use `tear_down_children=True`.

```python
Container.settings.override_sync(Settings(), tear_down_children=True)
```

### Tear down cached providers in tests and shutdown hooks

`Singleton` and `Resource` values are cached. Tear them down between tests or at application shutdown.

```python
import pytest_asyncio
from typing import AsyncIterator


@pytest_asyncio.fixture(autouse=True)
async def di_teardown() -> AsyncIterator[None]:
    try:
        yield
    finally:
        await Container.tear_down()
```

## Notes on advanced features

- `Generator` injection is supported, but generator injection cannot initialize `ContextResource` contexts for you. Pre-initialize the context first if needed.
- `Selector`, `Sequence`, and `Mapping` help compose providers instead of manually wiring branches and aggregates in application code.
- `State` is useful for runtime values that should flow through provider resolution.
- For framework integrations, see FastAPI, FastStream, and Litestar support in the docs.

## Practical defaults

When writing or reviewing code that uses `that-depends`, prefer these defaults:

1. Put providers on a `BaseContainer`.
2. Use `@inject` plus `Provide[Container.provider]`.
3. Avoid `resolve()` / `resolve_sync()` in application code.
4. Use `provider.context()` or `Container.context()` for context-managed dependencies.
5. Reach for `container_context()` only when multiple providers/containers, global context, or explicit scope control are required.
6. Use override APIs in tests and `tear_down()` in cleanup paths.

## Detailed documentation

For full package documentation, read the official docs: [https://that-depends.readthedocs.io/llms.txt](https://that-depends.readthedocs.io/llms.txt)
