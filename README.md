Modern DI
==
This package is dependency injection framework for Python

# Main principles:
1. Every dependency resolving is async, so you should construct with `await` keyword:
```python
some_dependency = await DIContainer.some_dependency()
```
2. No containers initialization to avoid wiring
