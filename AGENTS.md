# AGENTS.md

`that-depends` is a zero-dependency, typed dependency-injection framework for Python
3.10+. It is the org's most-used package and the only repo here with real external
contributor traffic: most merged PRs come from someone other than the maintainer.
Assume a human reviews your diff.

`modern-di` is the newer framework from the same author, and this repo links to it, but
`that-depends` is actively maintained rather than deprecated. Do not rewrite anything
here toward `modern-di`'s design, and do not carry conventions across in either
direction — the two repos diverge deliberately.

## Commands

`just` (task runner) and `uv` (package manager). The [`justfile`](justfile) is the
source of truth — `just --list`, or read it. Two behaviours to know before running
anything:

- `just lint` **rewrites files**. `just lint-ci` is the read-only twin and is what CI
  runs. Use `lint-ci` when you want an answer rather than a mutation.
- `just install` also installs the [`.pre-commit-config.yaml`](.pre-commit-config.yaml)
  hooks, so committing can change your working tree before the commit lands.
  `just unhook` removes them.

Type checking is **two** checkers — `mypy` in strict mode and `pyrefly` — and both must
be clean. There is no `ty` here, despite the org-level tooling note.

## Docs

Docs are MkDocs Material, but **Read the Docs builds and hosts them**
([`.readthedocs.yaml`](.readthedocs.yaml) → `docs/requirements.txt` → `mkdocs.yml`) —
not the GitHub Pages workflow the rest of the org uses. Two consequences:

- **Nothing builds the docs in CI.** A broken link or a bad snippet lands on `main` and
  only surfaces in the Read the Docs build afterwards. `just docs` serves the site
  locally, but it is `mkdocs serve` without `--strict`: a bad link warns in the log
  rather than failing, so read the output instead of just checking that the page renders.
- A user-facing page needs **two** entries in [`mkdocs.yml`](mkdocs.yml): the `nav` tree,
  and the `llmstxt` plugin's `sections`. Miss the second and the page is absent from
  `llms.txt` / `llms-full.txt`, which is what agent readers and the Context7 index
  ([`context7.json`](context7.json)) consume. The `dev/` and `migration/` pages are
  `nav`-only.

## The shipped agent skill

[`that_depends/.agents/skills/that-depends/SKILL.md`](that_depends/.agents/skills/that-depends/SKILL.md)
sits inside the package directory, so it **ships in the wheel** and users get it with
the dependency. Treat it as public surface: a change to recommended usage, a renamed
provider, or a new provider belongs there as well as in `docs/`.

## Architecture

Every module under `that_depends/` is named for what it does; read it. What a
single-file read will not tell you:

- **Containers are global, registered by name.** `BaseContainerMeta` keeps a
  process-wide `_instances` map (`meta.py`); that is what makes wiring-free injection
  and string injection (`Provide["Container.provider"]`) work. Two containers sharing a
  name warn and the later one wins, which bites tests that declare containers at module
  scope.
- **`default_scope` must be assigned before any `ContextResource` in a container body.**
  `_ContainerMetaDict.__setitem__` reads it while the class body is still executing and
  raises `DefaultScopeNotDefinedError` otherwise. Statement order inside the class body
  is load-bearing.
- **Every public operation has a sync and an async twin** — `resolve`/`resolve_sync`,
  `override`/`override_sync`, `tear_down`/`tear_down_sync`,
  `context_async`/`context_sync`. Adding one half of a pair is an incomplete change.

### Testing

`tests/container.py` holds the shared `DIContainer`, with resource creators split
between it and `tests/creators.py`; `tests/conftest.py` carries one autouse fixture that
resets overrides and tears the container down after each test. `pytest-randomly`
shuffles test order and `asyncio_mode` is `auto`, so a test that leaves provider state
behind fails somewhere else, non-deterministically. A test module that defines its own
container owns its own teardown.

CI runs the suite against **both** `faststream` major lines, so
`that_depends/integrations/faststream.py` has to work on each: a change there that only
passes locally is not verified. Coverage is uploaded to Codecov and the local run sets
no `fail_under`, so `just test` passing says nothing about coverage.

## Workflow

Fill in [`.github/PULL_REQUEST_TEMPLATE.md`](.github/PULL_REQUEST_TEMPLATE.md). It is
this repo's own copy, kept local because it names `mypy` and `pyrefly`, and contributors
do fill it in. Do not replace it with a free-form body, and do not edit the template.

Unlike the rest of the org, **you are not the last reader of your diff** — a second
party reviews and merges it. Write for them: what changed, why, and what you chose not
to do. Keep one PR to one thing.

PRs are squash-merged in practice and the merge subject is the PR title plus `(#N)`.
Conventional prefixes (`fix:`, `docs:`, `chore:`, `ci:`) are the norm for maintenance
work.

This repo has no `docs/adr/` and no `CONTEXT.md`. A decision that outlives the PR goes
in [`docs/dev/main-decisions.md`](docs/dev/main-decisions.md), which is a **user-facing
page** — write it for a reader of the docs site, not as an internal record. Real work
that is not scheduled becomes a GitHub issue on `modern-python/that-depends`
(`gh issue create`). There is no third place, and no truth-home directory: behaviour is
reviewed with the diff, not promoted to a page.

## Releases

`pyproject.toml` carries `version = "0"` as a placeholder. The published version comes
from the git tag — publishing triggers on a GitHub release and `just publish` runs
`uv version $GITHUB_REF_NAME`. **Never hand-edit `version`**; cut a release instead.

## Code style

- `ruff` (`select = ["ALL"]`, with an ignore list) and `mypy` in strict mode are
  configured in [`pyproject.toml`](pyproject.toml). Two consequences that catch new
  code: a public class, function or method without a docstring fails lint, and the
  package targets Python 3.10, so no 3.11+ syntax. `tests/` is exempt from the
  docstring and private-access rules.
- Docstrings use the `Args:` / `Returns:` form of `providers/base.py`, adding `Raises:`
  where a caller needs it (`injection.py`, `providers/selector.py`). State the contract;
  do not narrate the implementation.
