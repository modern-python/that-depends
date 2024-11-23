# Fixture

## Dependencies teardown

When using dependency injection in tests, it's important to properly tear down resources after tests complete.

Without proper teardown, the Python event loop might close before resources have a chance to shut down properly, leading to errors like `RuntimeError: Event loop is closed`. This can happen because pytest closes the event loop after test completion, but any remaining open connections or resources might still try to perform cleanup operations.

You can set up automatic teardown using a pytest fixture:

```python
import pytest_asyncio
from typing import AsyncGenerator

from my_project import DIContainer

@pytest_asyncio.fixture(autouse=True)
async def di_container_teardown() -> AsyncGenerator[None]:
    yield
    await DIContainer.tear_down()
```
