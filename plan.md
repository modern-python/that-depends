# Implementation Plan: Generic Dynamic Provider Resolution

## Overview

Rewrite PR #233 so dependency injection can prepare context resources for the active branch of any dynamic provider without importing or recognizing `Selector`. The implementation will add a small, additive provider-resolution contract, keep runtime-selection state alive only while the injected dependency is being resolved, preserve existing context-resource lifetimes, and restore the repository's 100% coverage baseline.

The current branch passes all 436 tests but reports 14 uncovered source lines and 99% total coverage. More importantly, its generic injection layer imports `Selector`, reaches into several provider-private attributes, duplicates sync and async graph walking, holds selector pins for the whole injected function in normal callables, and does not pin selector choices at all when generator injection has no resource stack.

## Goals

- Initialize only context resources reachable through the selected dynamic-provider branch.
- Evaluate a selector once per provider resolution and reuse that selection until resolution completes.
- Keep injection generic: no `Selector` import, `isinstance(Selector, ...)` branch, or selector-private access in `that_depends/injection.py`.
- Provide a useful additive extension point for future built-in and third-party dynamic providers.
- Preserve sync, async, direct, string-based, type-based, callable, and generator injection behavior.
- Finish with `just lint-ci` passing and `just test` reporting 100% total coverage.

## Architecture Decisions

### 1. Use a two-phase provider-resolution contract

Add default methods to `AbstractProvider` for two distinct dependency categories:

1. `get_resolution_dependencies()` exposes direct static prerequisites as a read-only `Collection[AbstractProvider[Any]]`. Its default implementation registers provider arguments when needed and returns the provider's registered parents without exposing mutable internal sets.
2. `resolution_context()` and `resolution_context_sync()` are async and sync context-manager hooks. They default to yielding an empty read-only collection. Dynamic providers override them to yield dependencies that can only be known after their static prerequisites are ready.

Dependency collections have no stable ordering guarantee. Dependency relationships, rather than collection order, determine initialization order.

`Selector` will keep its selector-key provider as a static prerequisite. Once that prerequisite's contexts are ready, its resolution context will choose one candidate, pin that choice with its private `ContextVar`, and yield only the chosen provider as a runtime dependency.

### 2. Separate resource lifetime from resolution-state lifetime

Injection will use two different stacks:

- The existing resource stack owns `ContextResource` instances and remains open for the injected function call.
- A new local resolution stack owns temporary provider state such as selector pins and closes immediately after the requested provider has resolved.

This prevents an injected selector choice from leaking into later provider resolutions performed inside the decorated function. A local resolution stack must exist even when the resource stack is `None`, so generator injection can still pin a dynamic choice while resolving providers that do not require context resources.

### 3. Traverse providers generically

For each provider resolution, injection will:

```text
visit provider
  -> visit its static resolution dependencies
  -> enter its resolution context
  -> visit the runtime dependencies yielded by that context
  -> initialize matching ContextResources on the resource stack
resolve the root provider while all resolution contexts remain active
close the resolution stack
```

Traversal will retain cycle and duplicate protection. Nested dynamic providers must use the same resolution stack as their root so every selected branch remains pinned until the root provider finishes resolving.

### 4. Keep compatibility additive

Existing provider subclasses that implement only `resolve()` and `resolve_sync()` continue to work through default no-op behavior. The new methods are supported public subclass extension points and must have complete types and docstrings. No existing public method, exception type, or error message will be removed or changed as part of this PR.

## Task List

### Task 1: Replace selector-specific injection traversal with the generic provider contract

**Description:** Implement the two-phase contract on `AbstractProvider`, adapt `Selector` to it, and rewrite sync and async injection preparation around a dedicated resolution stack. This is the core vertical slice and should replace—not layer on top of—the current PR implementation.

**Acceptance criteria:**

- [ ] `AbstractProvider` supplies typed, documented default implementations for static resolution dependencies and sync/async resolution contexts.
- [ ] `Selector` exposes its selector-key provider as a static dependency and yields only its selected candidate from its resolution context while the selection is pinned.
- [ ] `that_depends/injection.py` contains no import or concrete treatment of `Selector`, `ProviderWithArguments`, or selector state.
- [ ] Static and runtime dependency traversal shares cycle protection and works recursively in sync and async resolution.
- [ ] Resolution contexts close immediately after the root provider resolves; context resources retain their existing function-call lifetime.
- [ ] The rewrite does not add `SLF001` suppressions to injection code. Existing unavoidable suppressions unrelated to the new contract are not broadened.

**Verification:**

- [ ] Focused tests pass: `just test tests/providers/test_base.py tests/providers/test_selector.py tests/test_injection.py --no-cov`
- [ ] Ruff passes for touched source files: `uv run ruff check that_depends/providers/base.py that_depends/providers/selector.py that_depends/injection.py`
- [ ] Diff inspection confirms injection depends only on the generic provider contract.

**Dependencies:** None

**Files likely touched:**

- `that_depends/providers/base.py`
- `that_depends/providers/selector.py`
- `that_depends/injection.py`
- `tests/providers/test_selector.py`
- `tests/test_injection.py`

**Estimated scope:** Medium: 5 tightly related files

### Task 2: Prove the contract supports future dynamic providers

**Description:** Add a minimal test-only dynamic provider that uses the new contract without inheriting from or referring to `Selector`. Use it to verify that generic injection prepares static and runtime dependencies correctly, including nested dynamic providers.

**Acceptance criteria:**

- [ ] A custom `AbstractProvider` subclass can expose a runtime-selected dependency through the new public contract.
- [ ] Direct-provider injection resolves the custom provider in sync and async modes.
- [ ] A dynamic provider nested beneath an ordinary factory/singleton is discovered without concrete type checks.
- [ ] Nested dynamic providers retain every activation context until the root resolution completes.
- [ ] Duplicate and cyclic visits do not initialize or enter the same provider more than once during one root resolution.

**Verification:**

- [ ] Focused contract tests pass: `just test tests/providers/test_base.py tests/test_injection.py --no-cov`
- [ ] Type checking accepts a third-party-style subclass without casts or ignores: `uv run mypy tests/providers/test_base.py tests/test_injection.py --disable-error-code=unused-ignore`
- [ ] Pyrefly accepts the contract and test subclass: `uv run pyrefly check --no-progress-bar`

**Dependencies:** Task 1

**Files likely touched:**

- `tests/providers/test_base.py`
- `tests/test_injection.py`
- `that_depends/providers/base.py` only if the contract needs a type correction

**Estimated scope:** Small: 2-3 files

### Checkpoint: Generic resolution foundation

- [ ] Tasks 1-2 focused tests pass in both sync and async modes.
- [ ] No concrete dynamic-provider type appears in injection traversal.
- [ ] A test-only third-party provider demonstrates that the extension point is genuinely reusable.
- [ ] Review the public method names and lifetime documentation before expanding edge-case coverage.

### Task 3: Lock down Selector selection and lifetime semantics

**Description:** Add behavior-level regressions for `Selector` rather than tests of private registration fields. Cover the exact guarantees that motivated the rewrite: active branch only, exact-once selection, nested selection, override behavior, and cleanup.

**Acceptance criteria:**

- [ ] Sync and async selector callables are evaluated exactly once for each root provider resolution.
- [ ] Only the selected branch's context resources are entered; unselected sync and async resources remain untouched.
- [ ] A selected branch nested under another selector is prepared and resolved correctly.
- [ ] Selection state is reset after successful resolution and after exceptions.
- [ ] Resolving the same selector inside the decorated function performs a fresh selection, proving that injection did not pin it for the entire function body.
- [ ] An overridden selector does not activate any candidate branch.

**Verification:**

- [ ] Selector behavior tests pass: `just test tests/providers/test_selector.py tests/test_injection.py --no-cov`
- [ ] Tests assert observable lifecycle events and values rather than private `_parents`, `_children`, or pin state where possible.

**Dependencies:** Tasks 1-2

**Files likely touched:**

- `tests/providers/test_selector.py`
- `tests/test_injection.py`
- `that_depends/providers/selector.py` only if a behavior defect is exposed

**Estimated scope:** Medium: 2-3 files

### Task 4: Cover every injection surface and generator boundary

**Description:** Verify the generic mechanism through all supported provider lookup paths and through generator injection, where the resource stack is intentionally unavailable but a resolution stack is still required.

**Acceptance criteria:**

- [ ] Direct, string-based, and type-based injection all prepare a selected branch identically.
- [ ] Sync and async generators resolve a dynamic provider without context resources using one pinned selection.
- [ ] Generator injection still raises `ContextProviderError` when the selected branch requires a matching `ContextResource` and no resource stack exists.
- [ ] A context resource on an unselected branch does not cause generator injection to fail.
- [ ] Existing scope filtering remains unchanged: resources with a different scope are not entered or rejected.

**Verification:**

- [ ] Injection matrix passes: `just test tests/test_injection.py --no-cov`
- [ ] Existing generator and context-resource tests remain unchanged unless their assertions are strengthened.
- [ ] Coverage report attributes every new contract and traversal branch to a meaningful behavior test.

**Dependencies:** Task 3

**Files likely touched:**

- `tests/test_injection.py`
- `that_depends/injection.py` only if an uncovered behavior defect is exposed

**Estimated scope:** Medium: 1-2 files with a broad test matrix

### Checkpoint: Behavior complete

- [ ] Active-only traversal works for direct, nested, string, and type-based injection.
- [ ] Sync, async, generator, exception, and override lifetimes are covered.
- [ ] `just test` reports 100% total coverage with no `pragma: no cover` added for reachable behavior.

### Task 5: Remove the rejected implementation shape

**Description:** Remove obsolete helpers, imports, private-access suppressions, and tests that only validated the rejected concrete-`Selector` implementation shape.

**Acceptance criteria:**

- [ ] Tests no longer depend on the current PR's private registration implementation unless that private invariant has no observable substitute.
- [ ] The final diff removes the concrete `Selector` traversal, duplicated full graph walker, and associated new `# noqa: SLF001` comments from `injection.py`.
- [ ] No unused compatibility shim or redundant sync/async helper remains after the rewrite.

**Verification:**

- [ ] Ruff passes on all touched implementation and test files.
- [ ] Diff inspection confirms that every remaining branch implements a documented behavior covered by a test.

**Dependencies:** Task 4

**Files likely touched:**

- `tests/providers/test_selector.py`
- `that_depends/injection.py`
- `that_depends/providers/selector.py`

**Estimated scope:** Small: 3 files

### Task 6: Document the public extension contract

**Description:** Document the provider-resolution extension points and the observable `Selector` behavior for both provider authors and maintainers.

**Acceptance criteria:**

- [ ] `AbstractProvider` docstrings explain when static dependencies and resolution contexts are evaluated, how long contexts remain active, and what custom providers may yield.
- [ ] Selector documentation states that only the selected branch is prepared during injection and that selection is stable only for one provider resolution.
- [ ] The architectural decision is recorded for maintainers, including why resolution state and context-resource lifetime use separate stacks.
- [ ] Documentation does not expose private selector pinning or injection stack implementation details as public guarantees.

**Verification:**

- [ ] Documentation builds strictly: `uv run mkdocs build --strict`
- [ ] Public method names, type signatures, docstrings, and narrative documentation describe the same lifecycle.

**Dependencies:** Task 5

**Files likely touched:**

- `that_depends/providers/base.py`
- `docs/providers/selector.md`
- `docs/dev/main-decisions.md`

**Estimated scope:** Small: 3 files

### Task 7: Run authoritative repository gates

**Description:** Validate the complete rewrite using the repository's full lint, typing, test, and coverage gates. Fix only issues caused by this work and leave unrelated worktree changes untouched.

**Acceptance criteria:**

- [ ] Formatting, Ruff, mypy, and Pyrefly all pass without adding suppressions for the new contract.
- [ ] The complete randomized test suite passes.
- [ ] Coverage reports zero missing lines and 100% total coverage.
- [ ] The final PR description explains the generic contract and its semantics rather than presenting the work as a `Selector` special case.

**Verification:**

- [ ] `just lint-ci`
- [ ] `just test`
- [ ] Confirm the final coverage table reports `TOTAL ... 0 ... 100%`.
- [ ] Inspect `git diff --check` and `git diff origin/main...HEAD` for accidental or unrelated changes.

**Dependencies:** Task 6

**Files likely touched:** None beyond fixes directly required by the gates

**Estimated scope:** Small

### Checkpoint: Ready for review

- [ ] All task acceptance criteria are satisfied.
- [ ] `just lint-ci` passes.
- [ ] `just test` passes with 100% coverage.
- [ ] Injection has no knowledge of `Selector` or any other concrete dynamic provider.
- [ ] The public extension contract is typed, documented, and demonstrated by a non-Selector test provider.
- [ ] PR #233's review concern and Codecov failure are both resolved by the architecture rather than suppressed.

## Dependency Graph

```text
Task 1: provider contract + generic traversal
  -> Task 2: third-party extension proof
    -> Task 3: Selector semantics
      -> Task 4: injection and generator matrix
        -> Task 5: implementation cleanup
          -> Task 6: contract documentation
            -> Task 7: full repository gates
```

The tasks are intentionally sequential because they share one public contract. Test cases within Tasks 3 and 4 can be drafted independently after the Task 2 checkpoint, but implementation should not be parallelized until the method names and lifetime semantics are stable.

## Risks and Mitigations

| Risk | Impact | Mitigation |
|------|--------|------------|
| The new methods accidentally promise more ordering or lifecycle behavior than intended | High | Return immutable dependency collections, document ordering explicitly, and test only guaranteed behavior |
| Selector-key resources are needed before a candidate can be selected | High | Traverse static dependencies before entering the provider's runtime resolution context |
| Nested selector pins close before the root provider resolves | High | Enter all provider resolution contexts on one dedicated stack owned by the root resolution |
| Selection state leaks into the decorated function | High | Close the resolution stack immediately after `provider.resolve()` or `resolve_sync()` returns |
| Generator injection repeats selection because it has no resource stack | High | Always create a local resolution stack; keep `None` meaningful only for unavailable context-resource lifetime |
| Sync and async implementations drift | Medium | Use identical traversal structure and a shared behavior matrix with paired tests |
| Public method names collide with methods in third-party subclasses | Medium | Use resolution-specific names, keep defaults additive, and search the repository before finalizing names |
| Cyclic or shared dependency graphs cause repeated activation | Medium | Maintain a per-root-resolution visited set and add cycle/shared-dependency regression coverage |
| Tests reach 100% by asserting internals rather than behavior | Medium | Prefer event logs, returned values, evaluation counts, and resource enter/exit assertions |

## Not Doing

- Do not keep a structural or nominal `Selector` special case in injection.
- Do not initialize every selector candidate and filter afterward.
- Do not move general context-resource ownership into provider `resolve()` methods.
- Do not introduce a full `ProviderResolutionPlan` object or conditional-edge graph unless the two-phase contract proves insufficient.
- Do not keep selector pins alive for the full decorated function call.
- Do not add coverage exclusions, unreachable branches, or tests whose only purpose is executing dead defensive code.
- Do not change selector key validation, public error messages, override APIs, or unrelated provider behavior.
- Do not rewrite unrelated commits or files already merged from `main` into the PR branch.

## Open Questions

None are blocking. The plan selects `get_resolution_dependencies()`, `resolution_context()`, and `resolution_context_sync()` as supported subclass hooks returning read-only dependency collections with no ordering guarantee. If implementation reveals a concrete naming collision in downstream compatibility testing, rename the hooks before the Task 1 checkpoint and update the plan before proceeding.
