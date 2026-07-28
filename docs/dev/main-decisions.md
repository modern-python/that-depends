# Main decisions
1. Dependency resolving is async by default:
   - framework was developed mostly for usage with async python applications;
   - sync resolving is also possible, but it will fail in runtime in case of unresolved async dependencies;
2. Container is global:
   - it's needed for injections without wiring to work;
   - this way most of the logic stays in providers;
3. Focus on maximum compatibility with mypy:
   - no need for `# type: ignore`
   - no need for `typing.cast`
4. Provider preparation supports static and runtime dependencies:
   - `AbstractProvider.get_resolution_dependencies()` exposes prerequisites known before resolution;
   - `resolution_context()` and `resolution_context_sync()` expose dependencies selected only at runtime;
   - dependency collections are read-only and have no ordering guarantee beyond their dependency relationships;
   - injection keeps temporary provider-resolution state on a separate stack from `ContextResource` ownership. Resolution state ends as soon as the root provider resolves, preventing a dynamic choice from leaking into the decorated function, while context resources retain their existing function-call lifetime.
