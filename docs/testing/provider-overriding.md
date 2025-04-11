# Provider overriding

DI container provides, in addition to direct dependency injection, another very important functionality: 
**dependencies or providers overriding**.

Any provider registered with the container can be overridden. 
This can help you replace objects with simple stubs, or with other objects.
**Override affects all providers that use the overridden provider (_see example_)**.

## Example

```python
from pydantic_settings import BaseSettings
from sqlalchemy import create_engine, Engine, text
from testcontainers.postgres import PostgresContainer
from that_depends import BaseContainer, providers, Provide, inject


class SomeSQLADao:
    def __init__(self, *, sqla_engine: Engine):
        self.engine = sqla_engine
        self._connection = None

    def __enter__(self):
        self._connection = self.engine.connect()
        return self

    def __exit__(self, exc_type, exc_val, exc_tb):
        self._connection.close()

    def exec_query(self, query: str):
        return self._connection.execute(text(query))


class Settings(BaseSettings):
    db_url: str = 'some_production_db_url'


class DIContainer(BaseContainer):
    settings = providers.Singleton(Settings)
    sqla_engine = providers.Singleton(create_engine, settings.db_url)
    some_sqla_dao = providers.Factory(SomeSQLADao, sqla_engine=sqla_engine)


@inject
def exec_query_example(some_sqla_dao=Provide[DIContainer.some_sqla_dao]):
    with some_sqla_dao:
        result = some_sqla_dao.exec_query('SELECT 234')

    return next(result)


def main():
    pg_container = PostgresContainer(image='postgres:alpine3.19')
    pg_container.start()
    db_url = pg_container.get_connection_url()

    """
    We override only settings, but this override will also affect the 'sqla_engine' 
    and 'some_sqla_dao' providers because the 'settings' provider is used by them!
    """
    local_testing_settings = Settings(db_url=db_url)
    DIContainer.settings.override_sync(local_testing_settings)

    try:
        result = exec_query_example()
        assert result == (234,)
    finally:
        DIContainer.settings.reset_override_sync()
        pg_container.stop()


if __name__ == '__main__':
    main()

```

The example above shows how overriding a nested provider ('_settings_') 
affects another provider ('_engine_' and '_some_sqla_dao_').

## Override multiple providers

The example above looked at overriding only one settings provider, 
but the container also provides the ability to override 
multiple providers at once with method ```override_providers_sync```. 

The code above could remain the same except that 
the single provider override could be replaced with the following code:

```python
def main():
    pg_container = PostgresContainer(image='postgres:alpine3.19')
    pg_container.start()
    db_url = pg_container.get_connection_url()

    local_testing_settings = Settings(db_url=db_url)
    providers_for_overriding = {
        'settings': local_testing_settings,
        # more values...
    }
    with DIContainer.override_providers_sync(providers_for_overriding):
        try:
            result = exec_query_example()
            assert result == (234,)
        finally:
            pg_container.stop()
```

---
## Using with Litestar
In order to be able to inject dependencies of any type instead of existing objects, 
we need to **change the typing** for the injected parameter as follows:

```python3
import typing
from functools import partial
from typing import Annotated
from unittest.mock import Mock

from litestar import Litestar, Router, get
from litestar.di import Provide
from litestar.params import Dependency
from litestar.testing import TestClient

from that_depends import BaseContainer, providers


class ExampleService:
    def do_smth(self) -> str:
        return "something"


class DIContainer(BaseContainer):
    example_service = providers.Factory(ExampleService)


@get(path="/another-endpoint", dependencies={"example_service": Provide(DIContainer.example_service)})
async def endpoint_handler(
    example_service: Annotated[ExampleService, Dependency(skip_validation=True)],
) -> dict[str, typing.Any]:
    return {"object": example_service.do_smth()}


# or if you want a little less code
NoValidationDependency = partial(Dependency, skip_validation=True)


@get(path="/another-endpoint", dependencies={"example_service": Provide(DIContainer.example_service)})
async def endpoint_handler(
    example_service: Annotated[ExampleService, NoValidationDependency()],
) -> dict[str, typing.Any]:
    return {"object": example_service.do_smth()}


router = Router(
    path="/router",
    route_handlers=[endpoint_handler],
)

app = Litestar(route_handlers=[router])
```

Now we are ready to write tests with **overriding** and this will work with **any types**:

```python3
def test_litestar_endpoint_with_overriding() -> None:
    some_service_mock = Mock(do_smth=lambda: "mock func")

    with DIContainer.example_service.override_context_sync(some_service_mock), TestClient(app=app) as client:
        response = client.get("/router/another-endpoint")

    assert response.status_code == 200
    assert response.json()["object"] == "mock func"
```

More about `Dependency` 
in the [Litestar documentation](https://docs.litestar.dev/2/usage/dependency-injection.html#the-dependency-function).

---

## Overriding and tear-down

If you have a provider `A` that caches the resolved value, which depends on a provider
`B` that you wish to override you might experience the following behavior:

```python
class MyContainer(BaseContainer):
    B = providers.Singleton(lambda: 1)
    A = providers.Singleton(lambda x: x, B)


a_old = await MyContainer.A()

MyContainer.B.override_sync(32)  # will not reset A's cached value

a_new = await MyContainer.A()

assert a_old != a_new  # raises
```

This is due to the fact that `A` caches the value and doesn't get reset when you override `B`.

If you wish to fix this you can tell the provider to tear-down children on override:

```python
MyContainer.B.override_sync(32, tear_down_children=True)
```
