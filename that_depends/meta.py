import typing


if typing.TYPE_CHECKING:
    from that_depends.container import BaseContainer


class BaseContainerMeta(type):
    instances: typing.ClassVar[list[type["BaseContainer"]]] = []

    def __new__(cls, name: str, bases: tuple[type, ...], namespace: dict[str, typing.Any]) -> type:
        new_cls = super().__new__(cls, name, bases, namespace)
        if name != "BaseContainer":
            cls.instances.append(new_cls)  # type: ignore[arg-type]
        return new_cls

    @classmethod
    def get_instances(cls) -> list[type["BaseContainer"]]:
        return cls.instances
