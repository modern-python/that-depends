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
