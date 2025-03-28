import abc
import inspect
import typing

from typing_extensions import override

from that_depends.providers.base import AbstractProvider


T_co = typing.TypeVar("T_co", covariant=True)
P = typing.ParamSpec("P")


class AbstractFactory(AbstractProvider[T_co], abc.ABC):
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
        resource = factory.resolve_sync()  # "example-42"
        ```

    """

    __slots__ = "_args", "_factory", "_kwargs", "_override"

    def __init__(self, factory: typing.Callable[P, T_co], *args: typing.Any, **kwargs: typing.Any) -> None:  # noqa:ANN401
        """Initialize a Factory instance.

        Args:
            factory (Callable[P, T_co]): Function that returns the resource.
            *args: Arguments to pass to the factory function.
            **kwargs: Keyword arguments to pass to the factory function.

        """
        super().__init__()
        self._factory: typing.Final = factory
        self._args: typing.Final = args
        self._kwargs: typing.Final = kwargs
        self._register(self._args)
        self._register(self._kwargs.values())
        self._signature = inspect.signature(factory)
        self._has_var_keyword = self._check_var_keyword(self._signature)
        self._has_missing_kwargs: bool = self._requires_additional_kwargs(
            signature=self._signature, args=self._args, kwargs=self._kwargs, has_var_keyword=self._has_var_keyword
        )

    @override
    async def resolve(self, **kwargs: typing.Any) -> T_co:
        if self._override:
            return typing.cast(T_co, self._override)

        provided_args = [await x.resolve() if isinstance(x, AbstractProvider) else x for x in self._args]
        provided_kwargs = {
            k: await v.resolve() if isinstance(v, AbstractProvider) else v for k, v in self._kwargs.items()
        }
        if self._has_missing_kwargs:
            return self._call_with_relevant_args_kwargs_sync(
                self._factory, self._signature, provided_args, {**kwargs, **provided_kwargs}, self._has_var_keyword
            )
        return self._factory(*provided_args, **provided_kwargs)

    @override
    def resolve_sync(self, **kwargs: typing.Any) -> T_co:
        if self._override:
            return typing.cast(T_co, self._override)
        provided_args = [x.resolve_sync() if isinstance(x, AbstractProvider) else x for x in self._args]
        provided_kwargs = {
            k: v.resolve_sync() if isinstance(v, AbstractProvider) else v for k, v in self._kwargs.items()
        }

        if self._has_missing_kwargs:
            return self._call_with_relevant_args_kwargs_sync(
                self._factory, self._signature, provided_args, {**kwargs, **provided_kwargs}, self._has_var_keyword
            )
        return self._factory(*provided_args, **provided_kwargs)


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
        resource = await async_factory.resolve()  # "EXAMPLE"
        ```

    """

    __slots__ = "_args", "_factory", "_kwargs", "_override"

    def __init__(
        self,
        factory: typing.Callable[P, typing.Awaitable[T_co]],
        *args: typing.Any,  # noqa: ANN401
        **kwargs: typing.Any,  # noqa: ANN401
    ) -> None:
        """Initialize an AsyncFactory instance.

        Args:
            factory (Callable[P, Awaitable[T_co]]): Async function that returns the resource.
            *args: Arguments to pass to the factory function.
            **kwargs: Keyword arguments to pass to the factory


        """
        super().__init__()
        self._factory: typing.Final = factory
        self._args: typing.Final = args
        self._kwargs: typing.Final = kwargs
        self._register(self._args)
        self._register(self._kwargs.values())
        self._signature = inspect.signature(factory)
        self._has_var_keyword = self._check_var_keyword(self._signature)
        self._has_missing_kwargs: bool = self._requires_additional_kwargs(
            signature=self._signature, args=self._args, kwargs=self._kwargs, has_var_keyword=self._has_var_keyword
        )

    @override
    async def resolve(self, **kwargs: typing.Any) -> T_co:
        if self._override:
            return typing.cast(T_co, self._override)
        provided_args = [await x.resolve() if isinstance(x, AbstractProvider) else x for x in self._args]
        provided_kwargs = {
            k: await v.resolve() if isinstance(v, AbstractProvider) else v for k, v in self._kwargs.items()
        }
        if self._has_missing_kwargs:
            return await self._call_with_relevant_args_kwargs(
                func=self._factory,  # typing: ignore[arg-type]
                signature=self._signature,
                args=provided_args,
                kwargs={**kwargs, **provided_kwargs},
                has_var_keyword=self._has_var_keyword,
            )
        return await self._factory(*provided_args, **provided_kwargs)

    @override
    def resolve_sync(self, **kwargs: typing.Any) -> typing.NoReturn:
        msg = "AsyncFactory cannot be resolved synchronously"
        raise RuntimeError(msg)
