default: install lint test

install:
    uv lock --upgrade
    uv sync --all-extras --frozen

lint:
    uv run ruff format .
    uv run ruff check . --fix
    uv run mypy .

lint-ci:
    uv run ruff format . --check
    uv run ruff check . --no-fix
    uv run mypy .

test *args:
    uv run pytest {{ args }}

publish:
    rm -rf dist
    uv build
    uv publish --token $PYPI_TOKEN
