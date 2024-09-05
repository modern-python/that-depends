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
    rm -rf dist/*
    uv tool run --from build python -m build --installer uv
    uv tool run twine check dist/*
    uv tool run twine upload dist/* --username __token__ --password $PYPI_TOKEN
