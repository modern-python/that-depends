# The Dependency Injection Container

Containers serve as a central place to store and manage providers. You also define
your dependency graph in the containers.

While providers can be defined outside of containers with that depends, this is not recommended
if you want to use any [context features](../providers/context-resources.md)


## Quickstart

Define a container by subclassing `BaseContainer` and define your providers as class attributes.
```python
from that_depends import BaseContainer

class Container(BaseContainer):
    # define your providers here
```

Then you can build your dependency graph within the container:

```python
from that_depends import providers

class Container(BaseContainer):
    config = providers.Singleton(Config)
    session = providers.Factory(create_db_session, config=config.db) # (1)!
    
    user_repository = providers.Factory(
        UserRepository, 
        session=session.cast, # (3)!
        config.users
    ) # (2)!


```

1. The configuration will be resolved and then the `.db` attribute will be passed to the `create_db_session` creator
as a keyword argument when resolving the `session` provider.
2. Depends on both the session and configuration providers.
3. Providers have the `cast` property that will change their type to the return type of their creator, use it to prevent type errors.
