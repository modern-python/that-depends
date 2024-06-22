import dataclasses

import pydantic

from that_depends import BaseContainer, providers


@dataclasses.dataclass(kw_only=True, slots=True)
class SingletonFactory:
    dep1: str


class Settings(pydantic.BaseModel):
    some_setting: str = "some_value"
    other_setting: str = "other_value"


class DIContainer(BaseContainer):
    settings: Settings = providers.Singleton(Settings).cast
    singleton = providers.Singleton(SingletonFactory, dep1=settings.some_setting)


async def test_singleton_provider() -> None:
    singleton1 = await DIContainer.singleton()
    singleton2 = await DIContainer.singleton()
    singleton3 = DIContainer.singleton.sync_resolve()
    await DIContainer.singleton.tear_down()
    singleton4 = DIContainer.singleton.sync_resolve()

    assert singleton1 is singleton2 is singleton3
    assert singleton4 is not singleton1

    await DIContainer.tear_down()


async def test_singleton_attr_getter() -> None:
    singleton1 = await DIContainer.singleton()

    assert singleton1.dep1 == Settings().some_setting

    await DIContainer.tear_down()
