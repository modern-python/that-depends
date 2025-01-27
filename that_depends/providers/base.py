import abc
import contextlib
import inspect
import typing
from contextlib import contextmanager
from operator import attrgetter

import typing_extensions
from typing_extensions import override

from that_depends.entities.resource_context import ResourceContext


T_co = typing.TypeVar("T_co", covariant=True)
R = typing.TypeVar("R")
P = typing.ParamSpec("P")
ResourceCreatorType: typing.TypeAlias = typing.Callable[
    P,
    typing.Iterator[T_co] | typing.AsyncIterator[T_co] | typing.ContextManager[T_co] | typing.AsyncContextManager[T_co],
]


class AbstractProvider(typing.Generic[T_co], abc.ABC):
    """Base class for all providers."""

    def __init__(self, **kwargs: typing.Any) -> None:  # noqa: ANN401
        """Create a new provider."""
        super().__init__(**kwargs)
        self._override: typing.Any = None

    def __deepcopy__(self, *_: object, **__: object) -> typing_extensions.Self:
        """Hack for Litestar to prevent cloning object.

        More info here https://github.com/modern-python/that-depends/issues/119.
        """
        return self

    def __getattr__(self, attr_name: str) -> typing.Any:  # noqa: ANN401
        """Get an attribute from the resolve object.

        Args:
            attr_name: name of attribute to get.

        Returns:
            An `AttrGetter` provider that will get the attribute after resolving the current provider.

        """
        if attr_name.startswith("_"):
            msg = f"'{type(self)}' object has no attribute '{attr_name}'"
            raise AttributeError(msg)
        return AttrGetter(provider=self, attr_name=attr_name)

    @abc.abstractmethod
    async def async_resolve(self) -> T_co:
        """Resolve dependency asynchronously."""

    @abc.abstractmethod
    def sync_resolve(self) -> T_co:
        """Resolve dependency synchronously."""

    async def __call__(self) -> T_co:
        """Resolve dependency asynchronously."""
        return await self.async_resolve()

    def override(self, mock: object) -> None:
        """Override the provider with a mock object.

        Args:
            mock: object to resolve while the provider is overridden.

        Returns:
            None

        """
        self._override = mock

    @contextmanager
    def override_context(self, mock: object) -> typing.Iterator[None]:
        """Override the provider with a mock object temporarily.

        Args:
            mock: object to resolve while the provider is overridden.

        Returns:
            None

        """
        self.override(mock)
        try:
            yield
        finally:
            self.reset_override()

    def reset_override(self) -> None:
        """Reset the provider to its original state.

        Use this is you have previously called `override` or `override_context`
        to reset the provider to its original state.
        """
        self._override = None

    @property
    def cast(self) -> T_co:
        """Returns self, but cast to the type of the provided value.

        This helps to pass providers as input to other providers while avoiding type checking errors:

        Example:
            class A: ...

            def create_b(a: A) -> B: ...

            class Container(BaseContainer):
                a_factory = Factory(A)
                b_factory1 = Factory(create_b, a_factory)  # works, but mypy (or pyright, etc.) will complain
                b_factory2 = Factory(create_b, a_factory.cast)  # works and passes type checking

        """
        return typing.cast(T_co, self)


class AbstractResource(AbstractProvider[T_co], abc.ABC):
    """Base class for Resource providers."""

    def __init__(
        self,
        creator: ResourceCreatorType[P, T_co],
        *args: P.args,
        **kwargs: P.kwargs,
    ) -> None:
        """Create a new resource.

        Args:
            creator: sync or async iterator or context manager that yields resource.
            *args: positional arguments to pass to the creator.
            **kwargs: keyword arguments to pass to the creator.


        """
        super().__init__()
        self._creator: typing.Any

        if inspect.isasyncgenfunction(creator):
            self.is_async = True
            self._creator = contextlib.asynccontextmanager(creator)
        elif inspect.isgeneratorfunction(creator):
            self.is_async = False
            self._creator = contextlib.contextmanager(creator)
        elif isinstance(creator, type) and issubclass(creator, typing.AsyncContextManager):
            self.is_async = True
            self._creator = creator
        elif isinstance(creator, type) and issubclass(creator, typing.ContextManager):
            self.is_async = False
            self._creator = creator
        else:
            msg = "Unsupported resource type"
            raise TypeError(msg)
        self._args: P.args = args
        self._kwargs: P.kwargs = kwargs

    @abc.abstractmethod
    def _fetch_context(self) -> ResourceContext[T_co]: ...

    @override
    async def async_resolve(self) -> T_co:
        if self._override:
            return typing.cast(T_co, self._override)

        context = self._fetch_context()

        if context.instance is not None:
            return context.instance

        # lock to prevent race condition while resolving
        async with context.asyncio_lock:
            if context.instance is not None:
                return context.instance

            cm: typing.ContextManager[T_co] | typing.AsyncContextManager[T_co] = self._creator(
                *[await x.async_resolve() if isinstance(x, AbstractProvider) else x for x in self._args],
                **{
                    k: await v.async_resolve() if isinstance(v, AbstractProvider) else v
                    for k, v in self._kwargs.items()
                },
            )

            if isinstance(cm, typing.AsyncContextManager):
                context.context_stack = contextlib.AsyncExitStack()
                context.instance = await context.context_stack.enter_async_context(cm)

            elif isinstance(cm, typing.ContextManager):
                context.context_stack = contextlib.ExitStack()
                context.instance = context.context_stack.enter_context(cm)

            else:  # pragma: no cover
                typing.assert_never(cm)

        return context.instance

    @override
    def sync_resolve(self) -> T_co:
        if self._override:
            return typing.cast(T_co, self._override)

        context = self._fetch_context()
        if context.instance is not None:
            return context.instance

        if self.is_async:
            msg = "AsyncResource cannot be resolved synchronously"
            raise RuntimeError(msg)

        # lock to prevent race condition while resolving
        with context.threading_lock:
            if context.instance is not None:
                return context.instance

            cm = self._creator(
                *[x.sync_resolve() if isinstance(x, AbstractProvider) else x for x in self._args],
                **{k: v.sync_resolve() if isinstance(v, AbstractProvider) else v for k, v in self._kwargs.items()},
            )
            context.context_stack = contextlib.ExitStack()
            context.instance = context.context_stack.enter_context(cm)

            return context.instance


def _get_value_from_object_by_dotted_path(obj: typing.Any, path: str) -> typing.Any:  # noqa: ANN401
    attribute_getter = attrgetter(path)
    return attribute_getter(obj)


class AttrGetter(
    AbstractProvider[T_co],
):
    """Provides an attribute after resolving the wrapped provider."""

    __slots__ = "_attrs", "_provider"

    def __init__(self, provider: AbstractProvider[T_co], attr_name: str) -> None:
        """Create a new AttrGetter instance.

        Args:
            provider: provider to wrap.
            attr_name: attribute name to resolve when the provider is resolved.

        """
        super().__init__()
        self._provider = provider
        self._attrs = [attr_name]

    @override
    def __getattr__(self, attr: str) -> "AttrGetter[T_co]":
        if attr.startswith("_"):
            msg = f"'{type(self)}' object has no attribute '{attr}'"
            raise AttributeError(msg)
        self._attrs.append(attr)
        return self

    @override
    async def async_resolve(self) -> typing.Any:
        resolved_provider_object = await self._provider.async_resolve()
        attribute_path = ".".join(self._attrs)
        return _get_value_from_object_by_dotted_path(resolved_provider_object, attribute_path)

    @override
    def sync_resolve(self) -> typing.Any:
        resolved_provider_object = self._provider.sync_resolve()
        attribute_path = ".".join(self._attrs)
        return _get_value_from_object_by_dotted_path(resolved_provider_object, attribute_path)
