default: install lint test

install:
    uv lock --upgrade
    uv sync --all-extras --frozen
    @just hook

lint:
    uv run ruff format
    uv run ruff check --fix
    uv run mypy . --disable-error-code=unused-ignore
    uv run pyrefly check --no-progress-bar

lint-ci:
    uv run ruff format --check
    uv run ruff check --no-fix
    uv run mypy . --disable-error-code=unused-ignore
    uv run pyrefly check --no-progress-bar

adr_check_source := "https://raw.githubusercontent.com/modern-python/.github/main/tests/test_adr_citations.py"

# Tracks main on purpose: the shared check is unpinned.
adr-check:
    #!/usr/bin/env sh
    set -eu
    dir="$(mktemp -d .adr-check.XXXXXX)"
    trap 'rm -rf "$dir"' EXIT
    curl -fsSL "{{ adr_check_source }}" -o "$dir/test_adr_citations.py"
    uv run --no-sync pytest --rootdir=. --noconftest -o addopts= "$dir/test_adr_citations.py"

test *args:
    uv run --no-sync pytest {{ args }}

test-ci:
    uv run --no-sync pytest --cov=. --cov-report term-missing --cov-report xml

test-branch:
    @just test --cov=. --cov-branch

# Auth via PyPI Trusted Publishing (OIDC); uv publish auto-detects the CI id-token.
publish:
    rm -rf dist
    uv version $GITHUB_REF_NAME
    uv build
    uv publish

hook:
    uv run pre-commit install --install-hooks --overwrite

unhook:
    uv run pre-commit uninstall

docs:
    uvx --with-requirements docs/requirements.txt mkdocs serve
