# Application settings
For example, you have application settings in `pydantic_settings`
```python
import pydantic_settings


class Settings(pydantic_settings.BaseSettings):
    service_name: str = "FastAPI template"
    debug: bool = False
    ...
```

You can register settings as `Singleton` in DI container

```python
from that_depends import BaseContainer, providers


class DIContainer(BaseContainer):
    settings = providers.Singleton(Settings)
    settings_casted: Settings = settings.cast
    some_factory = providers.Factory(SomeFactory, service_name=settings_casted.service_name)
```

And when `some_factory` is resolved it will receive `service_name` attribute from `Settings`
