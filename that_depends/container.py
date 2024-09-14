import inspect
import typing
import warnings
from contextlib import contextmanager

from that_depends.providers import AbstractProvider, Resource, Singleton


if typing.TYPE_CHECKING:
    import typing_extensions


T = typing.TypeVar("T")
P = typing.ParamSpec("P")


class BaseContainer:
    providers: dict[str, AbstractProvider[typing.Any]]
    containers: list[type["BaseContainer"]]

    def __new__(cls, *_: typing.Any, **__: typing.Any) -> "typing_extensions.Self":  # noqa: ANN401
        msg = f"{cls.__name__} should not be instantiated"
        raise RuntimeError(msg)

    @classmethod
    def connect_containers(cls, *containers: type["BaseContainer"]) -> None:
        """Connect containers.

        When `init_resources` and `tear_down` is called,
        same method of connected containers will also be called.
        """
        if not hasattr(cls, "containers"):
            cls.containers = []

        cls.containers.extend(containers)

    @classmethod
    def get_providers(cls) -> dict[str, AbstractProvider[typing.Any]]:
        if not hasattr(cls, "providers"):
            cls.providers = {k: v for k, v in cls.__dict__.items() if isinstance(v, AbstractProvider)}

        return cls.providers

    @classmethod
    def get_containers(cls) -> list[type["BaseContainer"]]:
        if not hasattr(cls, "containers"):
            cls.containers = []

        return cls.containers

    @classmethod
    async def init_resources(cls) -> None:
        for provider in cls.get_providers().values():
            if isinstance(provider, Resource):
                await provider.async_resolve()

        for container in cls.get_containers():
            await container.init_resources()

    @classmethod
    async def init_async_resources(cls) -> None:
        warnings.warn("init_async_resources is deprecated, use init_resources instead", RuntimeWarning, stacklevel=1)
        await cls.init_resources()

    @classmethod
    async def tear_down(cls) -> None:
        for provider in reversed(cls.get_providers().values()):
            if isinstance(provider, Resource | Singleton):
                await provider.tear_down()

        for container in cls.get_containers():
            await container.tear_down()

    @classmethod
    def reset_override(cls) -> None:
        for v in cls.get_providers().values():
            v.reset_override()

    @classmethod
    def resolver(cls, item: type[T] | typing.Callable[P, T]) -> typing.Callable[[], typing.Awaitable[T]]:
        async def _inner() -> T:
            return await cls.resolve(item)

        return _inner

    @classmethod
    async def resolve(cls, object_to_resolve: type[T] | typing.Callable[..., T]) -> T:
        signature: typing.Final = inspect.signature(object_to_resolve)
        kwargs = {}
        providers: typing.Final = cls.get_providers()
        for field_name, field_value in signature.parameters.items():
            if field_value.default is not inspect.Parameter.empty or field_name in ("_", "__"):
                continue

            if field_name not in providers:
                msg = f"Provider is not found, {field_name=}"
                raise RuntimeError(msg)

            kwargs[field_name] = await providers[field_name].async_resolve()

        return object_to_resolve(**kwargs)

    @classmethod
    @contextmanager
    def override_providers(cls, providers_for_overriding: dict[str, typing.Any]) -> typing.Iterator[None]:
        current_providers: typing.Final = cls.get_providers()
        current_provider_names: typing.Final = set(current_providers.keys())
        given_provider_names: typing.Final = set(providers_for_overriding.keys())

        for given_name in given_provider_names:
            if given_name not in current_provider_names:
                msg = f"Provider with name {given_name!r} not found"
                raise RuntimeError(msg)

        for provider_name, mock in providers_for_overriding.items():
            provider = current_providers[provider_name]
            provider.override(mock)

        try:
            yield
        finally:
            for provider_name in providers_for_overriding:
                provider = current_providers[provider_name]
                provider.reset_override()
