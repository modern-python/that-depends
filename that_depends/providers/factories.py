import abc
import typing

from typing_extensions import override

from that_depends.providers.base import AbstractProvider


T_co = typing.TypeVar("T_co", covariant=True)
P = typing.ParamSpec("P")


class AbstractFactory(AbstractProvider[T_co], abc.ABC):
    """Base class for all factories."""

    @property
    def provider(self) -> typing.Callable[[], typing.Coroutine[typing.Any, typing.Any, T_co]]:
        """Get the sync provider function."""
        return self.async_resolve

    @property
    def sync_provider(self) -> typing.Callable[[], T_co]:
        """Get the async provider function."""
        return self.sync_resolve


class Factory(AbstractFactory[T_co]):
    """Provides an instance by calling a sync method."""

    __slots__ = "_args", "_factory", "_kwargs", "_override"

    def __init__(self, factory: typing.Callable[P, T_co], *args: P.args, **kwargs: P.kwargs) -> None:
        """Create a factory instance.

        Args:
            factory: function that returns the resource to be provided.
            *args: arguments to pass to the factory.
            **kwargs: keyword arguments to pass to the factory.

        """
        super().__init__()
        self._factory: typing.Final = factory
        self._args: typing.Final = args
        self._kwargs: typing.Final = kwargs

    @override
    async def async_resolve(self) -> T_co:
        if self._override:
            return typing.cast(T_co, self._override)

        return self._factory(
            *[  # type: ignore[arg-type]
                await x.async_resolve() if isinstance(x, AbstractProvider) else x for x in self._args
            ],
            **{  # type: ignore[arg-type]
                k: await v.async_resolve() if isinstance(v, AbstractProvider) else v for k, v in self._kwargs.items()
            },
        )

    @override
    def sync_resolve(self) -> T_co:
        if self._override:
            return typing.cast(T_co, self._override)

        return self._factory(
            *[  # type: ignore[arg-type]
                x.sync_resolve() if isinstance(x, AbstractProvider) else x for x in self._args
            ],
            **{  # type: ignore[arg-type]
                k: v.sync_resolve() if isinstance(v, AbstractProvider) else v for k, v in self._kwargs.items()
            },
        )


class AsyncFactory(AbstractFactory[T_co]):
    """Provides an instance by calling an async method."""

    __slots__ = "_args", "_factory", "_kwargs", "_override"

    def __init__(self, factory: typing.Callable[P, typing.Awaitable[T_co]], *args: P.args, **kwargs: P.kwargs) -> None:
        """Create an AsyncFactory instance.

        Args:
            factory: async callable that returns the required resource.
            *args: arguments to pass to the factory.
            **kwargs: keyword arguments to pass to the factory.

        """
        super().__init__()
        self._factory: typing.Final = factory
        self._args: typing.Final = args
        self._kwargs: typing.Final = kwargs

    @override
    async def async_resolve(self) -> T_co:
        if self._override:
            return typing.cast(T_co, self._override)

        return await self._factory(
            *[  # type: ignore[arg-type]
                await x.async_resolve() if isinstance(x, AbstractProvider) else x for x in self._args
            ],
            **{  # type: ignore[arg-type]
                k: await v.async_resolve() if isinstance(v, AbstractProvider) else v for k, v in self._kwargs.items()
            },
        )

    @override
    def sync_resolve(self) -> typing.NoReturn:
        msg = "AsyncFactory cannot be resolved synchronously"
        raise RuntimeError(msg)
