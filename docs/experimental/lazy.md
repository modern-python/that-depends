# Lazy Provider

The `LazyProvider` enables you to reference other providers without explicitly 
importing them into your module.

This can be helpful if you have a circular dependency between providers in 
multiple containers.


## Creating a Lazy Provider

=== "Single import string"
    ```python
    from that_depends.experimental import LazyProvider
    
    lazy_p = LazyProvider("full.import.string.including.attributes")
    ```
=== "Separate module and provider"
    ```python
    from that_depends.experimental import LazyProvider
    
    lazy_p = LazyProvider(module_string="my.module", provider_string="attribute.path")
    ```


## Usage

You can use the lazy provider in exactly the same way as you would use the referenced provider.

```python
# first_container.py
from that_depends import BaseContainer, providers, ContextScopes

def my_creator():
    yield 42

class FirstContainer(BaseContainer):
    value_provider = providers.ContextResource(my_creator).with_config(scope=ContextScopes.APP)
```

You can lazily import this provider:
```python
# second_container.py
from that_depends.experimental import LazyProvider
from that_depends import BaseContainer, providers
class SecondContainer(BaseContainer):
    lazy_value = LazyProvider("first_container.FirstContainer.value_provider")
    

with SecondContainer.lazy_value.context_sync(force=True):
    SecondContainer.lazy_value.resolve_sync() # 42
```
