default: install lint test

install:
    uv lock --upgrade
    uv sync --only-dev --frozen
    just hook

lint:
    uv run ruff format
    uv run ruff check --fix
    uv run mypy .

lint-ci:
    uv run ruff format --check
    uv run ruff check --no-fix
    uv run mypy .

test *args:
    uv run --no-sync pytest {{ args }}

publish:
    rm -rf dist
    uv build
    uv publish --token $PYPI_TOKEN

hook:
    uv run pre-commit install --install-hooks --overwrite

unhook:
    uv run pre-commit uninstall
