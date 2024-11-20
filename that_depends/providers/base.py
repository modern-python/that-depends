import abc
import contextlib
import inspect
import typing
from contextlib import contextmanager
from operator import attrgetter

import typing_extensions

from that_depends.entities.resource_context import ResourceContext


T_co = typing.TypeVar("T_co", covariant=True)
R = typing.TypeVar("R")
P = typing.ParamSpec("P")
ResourceCreatorType: typing.TypeAlias = typing.Callable[
    P,
    typing.Iterator[T_co] | typing.AsyncIterator[T_co] | typing.ContextManager[T_co] | typing.AsyncContextManager[T_co],
]


class AbstractProvider(typing.Generic[T_co], abc.ABC):
    def __init__(self) -> None:
        super().__init__()
        self._override: typing.Any = None

    def __deepcopy__(self, *_: object, **__: object) -> typing_extensions.Self:
        return self

    def __getattr__(self, attr_name: str) -> typing.Any:  # noqa: ANN401
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
        return await self.async_resolve()

    def override(self, mock: object) -> None:
        self._override = mock

    @contextmanager
    def override_context(self, mock: object) -> typing.Iterator[None]:
        self.override(mock)
        try:
            yield
        finally:
            self.reset_override()

    def reset_override(self) -> None:
        self._override = None

    @property
    def cast(self) -> T_co:
        """Returns self, but cast to the type of the provided value.

        This helps to pass providers as input to other providers while avoiding type checking errors:
        :example:

            class A: ...

            def create_b(a: A) -> B: ...

            class Container(BaseContainer):
                a_factory = Factory(A)
                b_factory1 = Factory(create_b, a_factory)  # works, but mypy (or pyright, etc.) will complain
                b_factory2 = Factory(create_b, a_factory.cast)  # works and passes type checking
        """
        return typing.cast(T_co, self)


class AbstractResource(AbstractProvider[T_co], abc.ABC):
    def __init__(
        self,
        creator: ResourceCreatorType[P, T_co],
        *args: P.args,
        **kwargs: P.kwargs,
    ) -> None:
        super().__init__()
        self._creator: typing.Any
        if inspect.isasyncgenfunction(creator):
            self._is_async = True
            self._creator = contextlib.asynccontextmanager(creator)
        elif inspect.isgeneratorfunction(creator):
            self._is_async = False
            self._creator = contextlib.contextmanager(creator)
        elif isinstance(creator, type) and issubclass(creator, typing.AsyncContextManager):
            self._is_async = True
            self._creator = creator
        elif isinstance(creator, type) and issubclass(creator, typing.ContextManager):
            self._is_async = False
            self._creator = creator
        else:
            msg = "Unsupported resource type"
            raise TypeError(msg)

        self._args: typing.Final[P.args] = args
        self._kwargs: typing.Final[P.kwargs] = kwargs

    @abc.abstractmethod
    def _fetch_context(self) -> ResourceContext[T_co]: ...

    async def async_resolve(self) -> T_co:
        if self._override:
            return typing.cast(T_co, self._override)

        context = self._fetch_context()

        if context.instance is not None:
            return context.instance

        if not context.is_async and self._is_async:
            msg = "AsyncResource cannot be resolved in an sync context."
            raise RuntimeError(msg)

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

    def sync_resolve(self) -> T_co:
        if self._override:
            return typing.cast(T_co, self._override)

        context = self._fetch_context()
        if context.instance is not None:
            return context.instance

        if self._is_async:
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
    __slots__ = "_provider", "_attrs"

    def __init__(self, provider: AbstractProvider[T_co], attr_name: str) -> None:
        super().__init__()
        self._provider = provider
        self._attrs = [attr_name]

    def __getattr__(self, attr: str) -> "AttrGetter[T_co]":
        if attr.startswith("_"):
            msg = f"'{type(self)}' object has no attribute '{attr}'"
            raise AttributeError(msg)
        self._attrs.append(attr)
        return self

    async def async_resolve(self) -> typing.Any:  # noqa: ANN401
        resolved_provider_object = await self._provider.async_resolve()
        attribute_path = ".".join(self._attrs)
        return _get_value_from_object_by_dotted_path(resolved_provider_object, attribute_path)

    def sync_resolve(self) -> typing.Any:  # noqa: ANN401
        resolved_provider_object = self._provider.sync_resolve()
        attribute_path = ".".join(self._attrs)
        return _get_value_from_object_by_dotted_path(resolved_provider_object, attribute_path)
