# Ecosystem

`that-depends` is part of the [`modern-python`](https://github.com/modern-python) organization —
a collection of open-source templates and libraries for production-ready Python applications.

## Newer DI framework: `modern-di`

If you're starting a new project, consider [`modern-di`](https://github.com/modern-python/modern-di) —
the newer DI framework from the same author. It ships as a small core plus a family of thin
framework adapters, in contrast to `that-depends`'s batteries-included approach.

`that-depends` remains actively maintained. The
[migration guide on the modern-di docs](https://modern-di.modern-python.org/migration/from-that-depends/)
walks through the API differences if you want to move an existing project across.

### `modern-di` family

| Package | What it does |
|---|---|
| [`modern-di`](https://github.com/modern-python/modern-di) | Core DI framework with scopes and groups |
| [`modern-di-fastapi`](https://github.com/modern-python/modern-di-fastapi) | FastAPI integration |
| [`modern-di-litestar`](https://github.com/modern-python/modern-di-litestar) | Litestar integration |
| [`modern-di-faststream`](https://github.com/modern-python/modern-di-faststream) | FastStream integration |
| [`modern-di-typer`](https://github.com/modern-python/modern-di-typer) | Typer (CLI) integration |
| [`modern-di-pytest`](https://github.com/modern-python/modern-di-pytest) | Pytest fixtures from DI providers |

## Project templates

End-to-end examples using `modern-di` for dependency injection:

- [`fastapi-sqlalchemy-template`](https://github.com/modern-python/fastapi-sqlalchemy-template) —
  dockerized web application with DI on FastAPI, SQLAlchemy 2, PostgreSQL
- [`litestar-sqlalchemy-template`](https://github.com/modern-python/litestar-sqlalchemy-template) —
  dockerized web application on LiteStar, SQLAlchemy 2, PostgreSQL

## Full project index

See the [`modern-python` organization profile](https://github.com/modern-python) for the
complete categorized list, including microservice utilities (`lite-bootstrap`, the
`faststream-*` family) and helper packages (`db-retry`, `eof-fixer`).