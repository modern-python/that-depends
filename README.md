"That Depends"
==
[![Test Coverage](https://codecov.io/gh/modern-python/that-depends/branch/main/graph/badge.svg)](https://codecov.io/gh/modern-python/that-depends)
[![MyPy Strict](https://img.shields.io/badge/mypy-strict-blue)](https://mypy.readthedocs.io/en/stable/getting_started.html#strict-mode-and-configuration)
[![pyrefly](https://img.shields.io/endpoint?url=https://pyrefly.org/badge.json)](https://github.com/facebook/pyrefly)
[![Supported versions](https://img.shields.io/pypi/pyversions/that-depends.svg)](https://pypi.python.org/pypi/that-depends)
[![PyPI Downloads](https://static.pepy.tech/badge/that-depends/month)](https://pepy.tech/projects/that-depends)
[![GitHub stars](https://img.shields.io/github/stars/modern-python/that-depends)](https://github.com/modern-python/that-depends/stargazers)
[![libs.tech recommends](https://libs.tech/project/773446541/badge.svg)](https://libs.tech/project/773446541/that-depends)
[![llms.txt](https://img.shields.io/badge/llms.txt-green)](https://that-depends.readthedocs.io/llms.txt)

Dependency injection framework for Python.

> **Starting a new project?** Also consider
> [`modern-di`](https://github.com/modern-python/modern-di), the newer DI framework from the
> same author with a smaller core and per-framework integration packages.
> `that-depends` remains fully supported — see [Ecosystem](#ecosystem) below.

It is production-ready and gives you the following:
- Simple async-first DI framework with IOC-container.
- Python 3.10+ support.
- Full coverage by types annotations (mypy in strict mode, pyrefly).
- Inbuilt FastAPI, FastStream and LiteStar compatibility.
- Dependency context management with scopes.
- Overriding dependencies for tests.
- Injecting dependencies in functions and coroutines without wiring.
- Package with zero dependencies.


### Installation
```bash
pip install that-depends
```

## Ecosystem

`that-depends` is part of the [`modern-python`](https://github.com/modern-python) family.
If you're starting a new project, consider [`modern-di`](https://github.com/modern-python/modern-di) —
the newer DI framework from the same author, with separate framework adapters:

- [`modern-di`](https://github.com/modern-python/modern-di) — core DI framework with scopes
- [`modern-di-fastapi`](https://github.com/modern-python/modern-di-fastapi),
  [`modern-di-litestar`](https://github.com/modern-python/modern-di-litestar),
  [`modern-di-faststream`](https://github.com/modern-python/modern-di-faststream),
  [`modern-di-typer`](https://github.com/modern-python/modern-di-typer),
  [`modern-di-pytest`](https://github.com/modern-python/modern-di-pytest)

`that-depends` remains actively maintained — see the
[migration guide](https://modern-di.readthedocs.io/latest/migration/from-that-depends/) if you
want to move existing projects across.

## 📚 [Documentation](https://that-depends.readthedocs.io)

## 📦 [PyPi](https://pypi.org/project/that-depends)

## 📝 [License](LICENSE)
