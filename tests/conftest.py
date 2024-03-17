import dataclasses
import modern_di


@dataclasses.dataclass(kw_only=True, slots=True)
class SomeFactory:
    dep1: str
    dep2: int


class DIContainer(modern_di.DeclarativeContainer):
    some_factory = modern_di.Factory(SomeFactory, dep1="text", dep2=123)
