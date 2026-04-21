import abc
import inspect
import typing
from typing import overload

from typing_extensions import override

from that_depends.providers.base import (
    AbstractProvider,
    _resolve_arguments,
    _resolve_arguments_sync,
    _resolve_keyword_arguments,
    _resolve_keyword_arguments_sync,
)
from that_depends.providers.mixin import ProviderWithArguments


T_co = typing.TypeVar("T_co", covariant=True)
P = typing.ParamSpec("P")


class AbstractFactory(ProviderWithArguments, AbstractProvider[T_co], abc.ABC):
    """Base class for all factories.

    This class defines the interface for factories that provide
    resources both synchronously and asynchronously.
    """

    @property
    def provider(self) -> typing.Callable[[], typing.Coroutine[typing.Any, typing.Any, T_co]]:
        """Returns an async provider function.

        The async provider function can be awaited to resolve the resource.

        Returns:
            Callable[[], Coroutine[Any, Any, T_co]]: The async provider function.

        Example:
            ```python
            provider = my_factory.provider
            resource = await provider()
            ```

        """
        return self.resolve

    @property
    def provider_sync(self) -> typing.Callable[[], T_co]:
        """Return a sync provider function.

        The sync provider function can be called to resolve the resource synchronously.

        Returns:
            Callable[[], T_co]: The sync provider function.

        Example:
            ```python
            provider = my_factory.provider_sync
            resource = provider()
            ```

        """
        return self.resolve_sync


class Factory(AbstractFactory[T_co]):
    """Provides an instance by calling a sync method.

    A typical usage scenario is to wrap a synchronous function
    that returns a resource. Each call to the provider or sync_provider
    produces a new instance of that resource.

    Example:
        ```python
        def build_resource(text: str, number: int):
            return f"{text}-{number}"

        factory = Factory(build_resource, "example", 42)
        resource = factory.provider_sync()  # "example-42"
        ```

    """

    def _register_arguments(self) -> None:
        if not self._mark_arguments_registered():
            return
        self._register(self._args)
        self._register(self._kwargs.values())

    def _deregister_arguments(self) -> None:
        raise NotImplementedError

    __slots__ = (
        "_args",
        "_args_are_providers",
        "_factory",
        "_kwargs",
        "_kwargs_are_providers",
        "_kwargs_items",
        "_override",
    )

    def __init__(self, factory: typing.Callable[P, T_co], *args: P.args, **kwargs: P.kwargs) -> None:
        """Initialize a Factory instance.

        Args:
            factory (Callable[P, T_co]): Function that returns the resource.
            *args: Arguments to pass to the factory function.
            **kwargs: Keyword arguments to pass to the factory function.

        """
        super().__init__()
        self._factory: typing.Final[typing.Callable[..., T_co]] = factory
        self._args: typing.Final = args
        self._kwargs: typing.Final = kwargs
        self._args_are_providers: typing.Final = tuple(isinstance(arg, AbstractProvider) for arg in args)
        self._kwargs_items: typing.Final = tuple(kwargs.items())
        self._kwargs_are_providers: typing.Final = tuple(
            isinstance(value, AbstractProvider) for _, value in self._kwargs_items
        )
        self._register_arguments()

    @override
    async def resolve(self) -> T_co:
        if self._override:
            return typing.cast(T_co, self._override)

        return self._factory(
            *await _resolve_arguments(self._args, self._args_are_providers),
            **await _resolve_keyword_arguments(self._kwargs_items, self._kwargs_are_providers),
        )

    @override
    def resolve_sync(self) -> T_co:
        if self._override:
            return typing.cast(T_co, self._override)

        return self._factory(
            *_resolve_arguments_sync(self._args, self._args_are_providers),
            **_resolve_keyword_arguments_sync(self._kwargs_items, self._kwargs_are_providers),
        )


class AsyncFactory(AbstractFactory[T_co]):
    """Provides an instance by calling an async method.

    Similar to `Factory`, but requires an async function. Each call
    to the provider or `provider` property is awaited to produce a new instance.

    Example:
        ```python
        async def async_build_resource(text: str):
            await some_async_operation()
            return text.upper()

        async_factory = AsyncFactory(async_build_resource, "example")
        resource = await async_factory.provider()  # "EXAMPLE"
        ```

    """

    def _register_arguments(self) -> None:
        if not self._mark_arguments_registered():
            return
        self._register(self._args)
        self._register(self._kwargs.values())

    def _deregister_arguments(self) -> None:
        raise NotImplementedError

    __slots__ = (
        "_args",
        "_args_are_providers",
        "_factory",
        "_kwargs",
        "_kwargs_are_providers",
        "_kwargs_items",
        "_override",
    )

    @overload
    def __init__(
        self, factory: typing.Callable[P, typing.Awaitable[T_co]], *args: P.args, **kwargs: P.kwargs
    ) -> None: ...

    @overload
    def __init__(self, factory: typing.Callable[P, T_co], *args: P.args, **kwargs: P.kwargs) -> None: ...

    def __init__(
        self, factory: typing.Callable[P, T_co | typing.Awaitable[T_co]], *args: P.args, **kwargs: P.kwargs
    ) -> None:
        """Initialize an AsyncFactory instance.

        Args:
            factory (Callable[P, T_co | Awaitable[T_co]]): Function that returns the resource (sync or async).
            *args: Arguments to pass to the factory function.
            **kwargs: Keyword arguments to pass to the factory


        """
        super().__init__()
        self._factory: typing.Final[typing.Callable[..., T_co | typing.Awaitable[T_co]]] = factory
        self._args: typing.Final = args
        self._kwargs: typing.Final = kwargs
        self._args_are_providers: typing.Final = tuple(isinstance(arg, AbstractProvider) for arg in args)
        self._kwargs_items: typing.Final = tuple(kwargs.items())
        self._kwargs_are_providers: typing.Final = tuple(
            isinstance(value, AbstractProvider) for _, value in self._kwargs_items
        )
        self._register_arguments()

    @override
    async def resolve(self) -> T_co:
        if self._override:
            return typing.cast(T_co, self._override)

        args = await _resolve_arguments(self._args, self._args_are_providers)
        kwargs = await _resolve_keyword_arguments(self._kwargs_items, self._kwargs_are_providers)

        result = self._factory(
            *args,
            **kwargs,
        )

        if inspect.isawaitable(result):
            return await result
        return result

    @override
    def resolve_sync(self) -> typing.NoReturn:
        msg = "AsyncFactory cannot be resolved synchronously"
        raise RuntimeError(msg)
