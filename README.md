"That Depends"
==
[![PyPI version](https://badge.fury.io/py/that-depends.svg)](https://pypi.python.org/pypi/that-depends)
[![Supported versions](https://img.shields.io/pypi/pyversions/that-depends.svg)](https://pypi.python.org/pypi/that-depends)
[![GitHub license](https://img.shields.io/github/license/modern-python/that-depends)](https://github.com/modern-python/that-depends/blob/main/LICENSE)
[![GitHub Actions Workflow Status](https://img.shields.io/github/actions/workflow/status/modern-python/that-depends/python-package.yml)](https://github.com/modern-python/that-depends/actions)
[![Doc](https://readthedocs.org/projects/that-depends/badge/?version=latest&style=flat)](https://that-depends.readthedocs.io)
[![GitHub stars](https://img.shields.io/github/stars/modern-python/that-depends)](https://github.com/modern-python/that-depends/stargazers)

This package is dependency injection framework for Python, mostly inspired by `python-dependency-injector`.

📚 [Documentation](https://that-depends.readthedocs.io)

It is production-ready and gives you the following:
- Fully-async simple DI framework with IOC-container.
- Python 3.10-3.12 support.
- Full coverage by types annotations (mypy in strict mode).
- FastAPI and Litestar compatibility.
- Zero dependencies.
- Overriding dependencies for tests.

# Projects with `That Depends`:
- [fastapi-sqlalchemy-template](https://github.com/modern-python/fastapi-sqlalchemy-template) - FastAPI template with sqlalchemy2 and PostgreSQL
- [litestar-sqlalchemy-template](https://github.com/modern-python/litestar-sqlalchemy-template) - LiteStar template with sqlalchemy2 and PostgreSQL

# Main decisions:
1. By default, dependency resolving is async:
```python
some_dependency = await DIContainer.dependent_factory()
```
2. Sync resolving is also possible, but will fail in case of async dependencies:
```python
sync_resource = DIContainer.sync_resource.sync_resolve()  # this will work
async_resource = DIContainer.async_resource.sync_resolve()  # this will fail with RuntimeError

# but this will work
async_resource = await DIContainer.async_resource()
async_resource = DIContainer.async_resource.sync_resolve()
```
3. No wiring for injections in function arguments -> achieved by decision that only one instance of container is supported
```python
from tests import container
from that_depends import Provide, inject

@inject
async def some_function(
    simple_factory: container.SimpleFactory = Provide[container.DIContainer.simple_factory],
) -> None:
    assert simple_factory.dep1
```

# Quickstart
## Install
```bash
pip install that-depends
```
