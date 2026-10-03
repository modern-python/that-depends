import ast
import pathlib
import re
import sys

import pytest

import that_depends


tomllib = pytest.importorskip("tomllib")

_PACKAGE_DIR = pathlib.Path(that_depends.__file__).parent
_INTEGRATIONS_DIR = _PACKAGE_DIR / "integrations"
_PROJECT = tomllib.loads((_PACKAGE_DIR.parent / "pyproject.toml").read_text())["project"]


def _top_level_imports(path: pathlib.Path) -> set[str]:
    roots: set[str] = set()
    for node in ast.parse(path.read_text()).body:
        if isinstance(node, ast.Import):
            roots.update(alias.name.split(".")[0] for alias in node.names)
        elif isinstance(node, ast.ImportFrom) and node.level == 0 and node.module:
            roots.add(node.module.split(".")[0])
    return roots


def _normalize(name: str) -> str:
    return re.sub(r"[-_.]+", "-", name).lower()


def _third_party_imports(paths: list[pathlib.Path]) -> set[str]:
    imported = set().union(*(_top_level_imports(path) for path in paths))
    return {_normalize(name) for name in imported if name not in sys.stdlib_module_names and name != "that_depends"}


def _declared(*, include_extras: bool) -> set[str]:
    requirements = list(_PROJECT.get("dependencies", []))
    if include_extras:
        requirements += [req for extra in _PROJECT.get("optional-dependencies", {}).values() for req in extra]
    return {_normalize(re.split(r"[\s;<>=!~\[]", requirement, maxsplit=1)[0]) for requirement in requirements}


def test_core_runtime_imports_are_unconditional_dependencies() -> None:
    core = [path for path in _PACKAGE_DIR.rglob("*.py") if _INTEGRATIONS_DIR not in path.parents]
    assert _third_party_imports(core) <= _declared(include_extras=False)


def test_integration_runtime_imports_are_declared_dependencies() -> None:
    integrations = list(_INTEGRATIONS_DIR.rglob("*.py"))
    assert _third_party_imports(integrations) <= _declared(include_extras=True)
