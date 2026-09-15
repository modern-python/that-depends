import ast
import os
import pathlib
import re
import typing


_REPO_ROOT: typing.Final = pathlib.Path(__file__).resolve().parent.parent
_ADR_DIR: typing.Final = "docs/adr/"
_CITATION: typing.Final = re.compile(r"docs/adr/\d{4}-[a-z0-9-]+\.md")
_UNWALKED_DIR: typing.Final = "node_modules"


def _python_files(root: pathlib.Path) -> list[pathlib.Path]:
    found: list[pathlib.Path] = []
    for dirpath, dirnames, filenames in os.walk(root):
        dirnames[:] = sorted(name for name in dirnames if not name.startswith(".") and name != _UNWALKED_DIR)
        found.extend(pathlib.Path(dirpath, name) for name in sorted(filenames) if name.endswith(".py"))
    return found


def _citations(source: str) -> set[str]:
    texts = [source]
    texts.extend(
        node.value
        for node in ast.walk(ast.parse(source))
        if isinstance(node, ast.Constant) and isinstance(node.value, str)
    )
    return {cited for text in texts for cited in _CITATION.findall(text)}


def unresolved_citations(root: pathlib.Path) -> list[tuple[str, str]]:
    return sorted(
        (file.relative_to(root).as_posix(), cited)
        for file in _python_files(root)
        for cited in _citations(file.read_text(encoding="utf-8"))
        if not (root / cited).is_file()
    )


def test_every_adr_path_cited_from_python_resolves() -> None:
    """INVARIANT: a `docs/adr/NNNN-<slug>.md` path named anywhere in this repo's Python exists.

    Broken by renaming, renumbering or pruning an ADR without following its citations. The
    offline link gate reads Markdown only, so a path in a docstring, a comment or a guard message
    is otherwise checked by nothing, and an `INVARIANT:` docstring that names its ADR silently
    loses the rationale the test depends on. A user who trips a guard is handed a link to follow.
    """
    unresolved = unresolved_citations(_REPO_ROOT)

    assert unresolved == [], "\n".join(f"{file} cites {cited}" for file, cited in unresolved)


def test_a_citation_of_a_missing_adr_is_reported_with_its_citing_file(tmp_path: pathlib.Path) -> None:
    """The scanner is exercised against a known result, so an empty scan cannot pass as a green one."""
    (tmp_path / _ADR_DIR).mkdir(parents=True)
    (tmp_path / _ADR_DIR / "0001-kept.md").write_text("# kept\n", encoding="utf-8")
    (tmp_path / "pkg").mkdir()
    (tmp_path / "pkg" / "mod.py").write_text(
        f'"""Explained in {_ADR_DIR}0001-kept.md and {_ADR_DIR}9999-missing.md."""\n',
        encoding="utf-8",
    )

    assert unresolved_citations(tmp_path) == [("pkg/mod.py", f"{_ADR_DIR}9999-missing.md")]


def test_a_citation_split_across_adjacent_string_literals_is_found(tmp_path: pathlib.Path) -> None:
    """Python joins adjacent literals at parse time, which is what the `nack` guard message relies on."""
    (tmp_path / "guard.py").write_text(
        f'MESSAGE = (\n    "See https://example.invalid/blob/main/{_ADR_DIR}"\n    "0003-split.md."\n)\n',
        encoding="utf-8",
    )

    assert unresolved_citations(tmp_path) == [("guard.py", f"{_ADR_DIR}0003-split.md")]


def test_a_citation_inside_a_hash_comment_is_found(tmp_path: pathlib.Path) -> None:
    """Comments never reach the AST, so the raw text is scanned as well."""
    (tmp_path / "graph.py").write_text(f"# The rule is one-way, see {_ADR_DIR}0009-comment.md\n", encoding="utf-8")

    assert unresolved_citations(tmp_path) == [("graph.py", f"{_ADR_DIR}0009-comment.md")]


def test_a_tree_with_no_citations_and_no_adr_directory_reports_nothing(tmp_path: pathlib.Path) -> None:
    (tmp_path / "plain.py").write_text("X = 1\n", encoding="utf-8")

    assert unresolved_citations(tmp_path) == []


def test_files_under_dot_directories_are_not_scanned(tmp_path: pathlib.Path) -> None:
    """A virtualenv or a cache is not this repo's citations."""
    (tmp_path / ".venv" / "lib").mkdir(parents=True)
    (tmp_path / ".venv" / "lib" / "vendored.py").write_text(f"# {_ADR_DIR}0001-elsewhere.md\n", encoding="utf-8")
    (tmp_path / _UNWALKED_DIR).mkdir()
    (tmp_path / _UNWALKED_DIR / "dep.py").write_text(f"# {_ADR_DIR}0002-elsewhere.md\n", encoding="utf-8")

    assert unresolved_citations(tmp_path) == []
