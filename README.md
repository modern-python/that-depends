# that-depends

[![PyPI version](https://img.shields.io/pypi/v/that-depends.svg)](https://pypi.org/project/that-depends/)
[![Supported Python versions](https://img.shields.io/pypi/pyversions/that-depends.svg)](https://pypi.org/project/that-depends/)
[![Downloads](https://img.shields.io/pypi/dm/that-depends.svg)](https://pypistats.org/packages/that-depends)
[![Test Coverage](https://codecov.io/gh/modern-python/that-depends/branch/main/graph/badge.svg)](https://codecov.io/gh/modern-python/that-depends)
[![CI](https://github.com/modern-python/that-depends/actions/workflows/ci.yml/badge.svg)](https://github.com/modern-python/that-depends/actions/workflows/ci.yml)
[![License](https://img.shields.io/github/license/modern-python/that-depends.svg)](https://github.com/modern-python/that-depends/blob/main/LICENSE)
[![GitHub stars](https://img.shields.io/github/stars/modern-python/that-depends)](https://github.com/modern-python/that-depends/stargazers)
[![MyPy Strict](https://img.shields.io/badge/mypy-strict-blue)](https://mypy.readthedocs.io/en/stable/getting_started.html#strict-mode-and-configuration)
[![pyrefly](https://img.shields.io/endpoint?url=https://pyrefly.org/badge.json)](https://github.com/facebook/pyrefly)
[![libs.tech recommends](https://libs.tech/project/773446541/badge.svg)](https://libs.tech/project/773446541/that-depends)
[![Context7](https://img.shields.io/badge/Context7-docs-blue)](https://context7.com/modern-python/that-depends)
[![llms.txt](https://img.shields.io/badge/llms.txt-green)](https://that-depends.modern-python.org/llms.txt)

Simple, typed dependency injection framework for Python.

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
[migration guide](https://modern-di.modern-python.org/migration/from-that-depends/) if you
want to move existing projects across.

## 📚 [Documentation](https://that-depends.modern-python.org)

## 📦 [PyPI](https://pypi.org/project/that-depends)

## 📝 [License](LICENSE)

## Part of `modern-python`

Browse the full list of templates and libraries in
[`modern-python`](https://github.com/modern-python) — see the org profile for the categorized index.
