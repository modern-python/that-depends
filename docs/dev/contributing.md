# Contributing
`that-depends` is an opensource project, and we are opened to new contributors.

## Getting started
1. Make sure that you have [uv](https://docs.astral.sh/uv/) and [just](https://just.systems/) installed.
2. Clone project:
```
git@github.com:modern-python/that-depends.git
cd that-depends
```
3. Install dependencies running `just install`

## Running linters
`Ruff` is used for linting and formatting; `mypy` and `pyrefly` for type checking.

Run all checks by command `just lint`. This rewrites files: use `just lint-ci` for a read-only run.

## Running tests
Run all tests by command `just test`

## Building and running the documentation
Host the documentation locally by running `just docs`
