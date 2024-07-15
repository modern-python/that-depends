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
    DIContainer.settings.override(local_testing_settings)

    try:
        result = exec_query_example()
        assert result == (234,)
    finally:
        DIContainer.settings.reset_override()
        pg_container.stop()


if __name__ == '__main__':
    main()

```

The example above shows how overriding a nested provider ('_settings_') 
affects another provider ('_engine_' and '_some_sqla_dao_').

## Override multiple providers

The example above looked at overriding only one settings provider, 
but the container also provides the ability to override 
multiple providers at once with method ```override_providers```. 

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
    with DIContainer.override_providers(providers_for_overriding):
        try:
            result = exec_query_example()
            assert result == (234,)
        finally:
            pg_container.stop()
```
