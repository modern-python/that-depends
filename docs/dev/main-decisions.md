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
4. The only runtime dependency is `typing-extensions`:
   - it backports `override` to Python 3.11, and `TypeIs`, `TypeVar` defaults and `deprecated` to Python 3.11 and 3.12;
   - integrations declare their own imports in extras, and `tests/test_packaging.py` checks both.

## Python support policy

Minor releases may drop Python versions that have reached
[upstream end of life](https://devguide.python.org/versions/). A Python support drop
alone does not require a major release. Patch releases retain the minimum Python
version of their minor release series.

Support drops are announced prominently in the release notes, and package metadata
declares the minimum supported Python version through `Requires-Python`. Installers
such as pip use this metadata to select a compatible release, provided it also
satisfies the application's dependency constraints. Older releases remain available;
continued fixes for an older release series are not guaranteed.

### Python 3.10 and version 4.3.0

**Breaking:** that-depends 4.3.0 requires Python 3.11 or newer. Python 3.10 reached
[end of life on October 1, 2026](https://peps.python.org/pep-0619/).

Applications staying on Python 3.10 should require `that-depends<4.3`. The 4.2 series
supports Python 3.10; 4.2.1 is the latest compatible release when preparing 4.3.0.
Upgrading to Python 3.11 or newer allows installation of 4.3.0 without changing the
application's use of the that-depends API.
