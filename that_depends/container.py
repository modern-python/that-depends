import inspect
import typing
from contextlib import contextmanager
from typing import overload

from typing_extensions import override

from that_depends.meta import BaseContainerMeta
from that_depends.providers import AbstractProvider, AsyncSingleton, Resource, Singleton
from that_depends.providers.context_resources import ContextScope, ContextScopes


if typing.TYPE_CHECKING:
    import typing_extensions


T = typing.TypeVar("T")
P = typing.ParamSpec("P")


class BaseContainer(metaclass=BaseContainerMeta):
    """Base container class."""

    alias: str | None = None
    providers: dict[str, AbstractProvider[typing.Any]]
    containers: list[type["BaseContainer"]]
    default_scope: ContextScope | None = ContextScopes.ANY

    @classmethod
    @overload
    def context(cls, func: typing.Callable[P, T]) -> typing.Callable[P, T]: ...

    @classmethod
    @overload
    def context(cls, *, force: bool = False) -> typing.Callable[[typing.Callable[P, T]], typing.Callable[P, T]]: ...

    @classmethod
    def context(
        cls, func: typing.Callable[P, T] | None = None, force: bool = False
    ) -> typing.Callable[P, T] | typing.Callable[[typing.Callable[P, T]], typing.Callable[P, T]]:
        """Wrap a function with this resources' context.

        Args:
            func: function to be wrapped.
            force: force context initialization, ignoring scope.

        Returns:
            wrapped function or wrapper if func is None.

        """

        def _wrapper(func: typing.Callable[P, T]) -> typing.Callable[P, T]:
            if inspect.iscoroutinefunction(func):

                async def _async_wrapper(*args: P.args, **kwargs: P.kwargs) -> T:
                    async with cls.context_async(force=force):
                        return await func(*args, **kwargs)  # type: ignore[no-any-return]

                return typing.cast(typing.Callable[P, T], _async_wrapper)

            def _sync_wrapper(*args: P.args, **kwargs: P.kwargs) -> T:
                with cls.context_sync(force=force):
                    return func(*args, **kwargs)

            return _sync_wrapper

        if func:
            return _wrapper(func)
        return _wrapper

    @override
    def __new__(cls, *_: typing.Any, **__: typing.Any) -> "typing_extensions.Self":
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
    async def init_resources(cls) -> None:
        """Initialize all resources."""
        for provider in cls.get_providers().values():
            if isinstance(provider, Resource | Singleton | AsyncSingleton):
                await provider.resolve()

        for container in cls.get_containers():
            await container.init_resources()

    @classmethod
    def reset_override_sync(cls) -> None:
        """Reset all provider overrides."""
        for v in cls.get_providers().values():
            v.reset_override_sync()

    @classmethod
    def resolver(cls, item: typing.Callable[P, T]) -> typing.Callable[[], typing.Awaitable[T]]:
        """Decorate a function to automatically resolve dependencies on call by name.

        Args:
            item: objects for which the dependencies should be resolved.

        Returns:
            Async wrapped callable with auto-injected dependencies.

        """

        async def _inner() -> T:
            return await cls.resolve(item)

        return _inner

    @classmethod
    async def resolve(cls, object_to_resolve: typing.Callable[..., T]) -> T:
        """Inject dependencies into an object automatically by name."""
        signature: typing.Final = inspect.signature(object_to_resolve)
        kwargs = {}
        providers: typing.Final = cls.get_providers()
        for field_name, field_value in signature.parameters.items():
            if field_value.default is not inspect.Parameter.empty or field_name in ("_", "__"):
                continue

            if field_name not in providers:
                msg = f"Provider is not found, {field_name=}"
                raise RuntimeError(msg)

            kwargs[field_name] = await providers[field_name].resolve()

        return object_to_resolve(**kwargs)

    @classmethod
    @contextmanager
    def override_providers_sync(cls, providers_for_overriding: dict[str, typing.Any]) -> typing.Iterator[None]:
        """Override several providers with mocks simultaneously.

        Args:
            providers_for_overriding: {provider_name: mock} dictionary.

        Returns:
            None

        """
        current_providers: typing.Final = cls.get_providers()
        current_provider_names: typing.Final = set(current_providers.keys())
        given_provider_names: typing.Final = set(providers_for_overriding.keys())

        for given_name in given_provider_names:
            if given_name not in current_provider_names:
                msg = f"Provider with name {given_name!r} not found"
                raise RuntimeError(msg)

        for provider_name, mock in providers_for_overriding.items():
            provider = current_providers[provider_name]
            provider.override_sync(mock)

        try:
            yield
        finally:
            for provider_name in providers_for_overriding:
                provider = current_providers[provider_name]
                provider.reset_override_sync()
