
# DictProvider
- It allows you to logically group related dependencies together in a dictionary, making it easier to manage and inject them as a single unit.
- It simplifies the injection process when multiple dependencies need to be passed to a component that expects a dictionary of dependencies.

## Example Usage
### Step 1: Define the Dependencies
```python
@dataclasses.dataclass(kw_only=True, slots=True)
class ModuleA:
    dependency: str


@dataclasses.dataclass(kw_only=True, slots=True)
class ModuleB:
    dependency: str


@dataclasses.dataclass(kw_only=True, slots=True)
class Dispatcher:
    modules: Dict[str, Any]

```
### Step 2: Define Providers
Next, define the providers for these dependencies using `Factory` and `DictProvider`.

```python
class DIContainer(BaseContainer):
    module_a_provider = providers.Factory(ModuleA, dependency="some_dependency_a")
    module_b_provider = providers.Factory(ModuleB, dependency="some_dependency_b")
    modules_provider = providers.DictProvider(module1=module_a_provider, module2=module_b_provider)
    dispatcher_provider = providers.Factory(Dispatcher, modules=modules_provider)
```

### Step 3: Resolve the Dispatcher
```
dispatcher = DIContainer.dispatcher_provider.sync_resolve()

print(dispatcher.modules["module1"].dependency)  # Output: some_dependency_a
print(dispatcher.modules["module2"].dependency)  # Output: some_dependency_b

# Asynchronous usage example
import asyncio

async def main():
    dispatcher_async = await container.dispatcher_provider.async_resolve()
    print(dispatcher_async.modules["module1"].dependency)  # Output: real_dependency_a
    print(dispatcher_async.modules["module2"].dependency)  # Output: real_dependency_b

asyncio.run(main())
```