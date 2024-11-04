import abc
import asyncio
import contextlib
import inspect
import typing
from contextlib import contextmanager
from operator import attrgetter


T_co = typing.TypeVar("T_co", covariant=True)
R = typing.TypeVar("R")
P = typing.ParamSpec("P")


class AbstractProvider(typing.Generic[T_co], abc.ABC):
    """Abstract Provider Class."""

    def __init__(self) -> None:
        super().__init__()
        self._override: typing.Any = None

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


class ResourceContext(typing.Generic[T_co]):
    __slots__ = "context_stack", "instance", "resolving_lock", "is_async"

    def __init__(self, is_async: bool) -> None:
        """Create a new ResourceContext instance.

        :param is_async: Whether the ResourceContext was created in an async context.
        For example within a ``async with container_context(): ...`` statement.
        :type is_async: bool
        """
        self.instance: T_co | None = None
        self.resolving_lock: typing.Final = asyncio.Lock()
        self.context_stack: contextlib.AsyncExitStack | contextlib.ExitStack | None = None
        self.is_async = is_async

    @staticmethod
    def is_context_stack_async(
        context_stack: contextlib.AsyncExitStack | contextlib.ExitStack | None,
    ) -> typing.TypeGuard[contextlib.AsyncExitStack]:
        return isinstance(context_stack, contextlib.AsyncExitStack)

    @staticmethod
    def is_context_stack_sync(
        context_stack: contextlib.AsyncExitStack | contextlib.ExitStack,
    ) -> typing.TypeGuard[contextlib.ExitStack]:
        return isinstance(context_stack, contextlib.ExitStack)

    async def tear_down(self) -> None:
        """Async tear down the context stack."""
        if self.context_stack is None:
            return

        if self.is_context_stack_async(self.context_stack):
            await self.context_stack.aclose()
        elif self.is_context_stack_sync(self.context_stack):
            self.context_stack.close()
        self.context_stack = None
        self.instance = None

    def sync_tear_down(self) -> None:
        """Sync tear down the context stack.

        :raises RuntimeError: If the context stack is async and the tear down is called in sync mode.
        """
        if self.context_stack is None:
            return

        if self.is_context_stack_sync(self.context_stack):
            self.context_stack.close()
            self.context_stack = None
            self.instance = None
        elif self.is_context_stack_async(self.context_stack):
            msg = "Cannot tear down async context in sync mode"
            raise RuntimeError(msg)


ResourceCreator: typing.TypeAlias = (
    typing.Callable[
        P,
        typing.Iterator[T_co]
        | typing.AsyncIterator[T_co]
        | typing.ContextManager[T_co]
        | typing.AsyncContextManager[T_co],
    ]
    | typing.ContextManager[T_co]
    | typing.AsyncContextManager[T_co]
)


class AbstractResource(AbstractProvider[T_co], abc.ABC):
    def __init__(
        self,
        creator: ResourceCreator[P, T_co],
        *args: P.args,
        **kwargs: P.kwargs,
    ) -> None:
        super().__init__()
        is_async, normalized_creator = _ResourceCreatorNormalizer.normalize(self, creator, *args, **kwargs)
        self._is_async = is_async
        self._creator: typing.Final[
            typing.Callable[P, typing.ContextManager[T_co] | typing.AsyncContextManager[T_co]]
        ] = normalized_creator
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

        # lock to prevent race condition while resolving
        async with context.resolving_lock:
            if context.instance is None:
                cm = self._creator(
                    *[await x.async_resolve() if isinstance(x, AbstractProvider) else x for x in self._args],
                    **{
                        k: await v.async_resolve() if isinstance(v, AbstractProvider) else v
                        for k, v in self._kwargs.items()
                    },
                )

                if isinstance(cm, typing.AsyncContextManager):
                    if not context.is_async:
                        msg = "AsyncResource cannot be resolved in an sync context."
                        raise RuntimeError(msg)

                    context.context_stack = contextlib.AsyncExitStack()
                    context.instance = await context.context_stack.enter_async_context(cm)

                elif isinstance(cm, typing.ContextManager):
                    context.context_stack = contextlib.ExitStack()
                    context.instance = context.context_stack.enter_context(cm)

                else:
                    typing.assert_never(cm)

        return context.instance

    def sync_resolve(self) -> T_co:
        if self._override:
            return typing.cast(T_co, self._override)

        context = self._fetch_context()
        if context.instance is not None:
            return context.instance

        cm = self._creator(
            *[x.sync_resolve() if isinstance(x, AbstractProvider) else x for x in self._args],
            **{k: v.sync_resolve() if isinstance(v, AbstractProvider) else v for k, v in self._kwargs.items()},
        )

        if isinstance(cm, typing.AsyncContextManager):
            msg = "AsyncResource cannot be resolved synchronously"
            # TODO(zerlok): change to TypeError # noqa: TD003, FIX002
            raise RuntimeError(msg, cm)  # noqa: TRY004

        context.context_stack = contextlib.ExitStack()
        context.instance = context.context_stack.enter_context(cm)

        return context.instance


class _ResourceCreatorNormalizer:
    # TODO(zerlok): simplify code in function # noqa: TD003, FIX002
    @classmethod
    def normalize(  # noqa: C901
        cls,
        resource: object,
        creator: ResourceCreator[P, T_co],
        *args: P.args,
        **kwargs: P.kwargs,
    ) -> tuple[bool, typing.Callable[P, typing.ContextManager[T_co] | typing.AsyncContextManager[T_co]]]:
        match creator:
            case cm_async if cls._check_creator_is_async_context_manager(cm_async):
                if args or kwargs:
                    msg = "AsyncContextManager does not accept any arguments"
                    raise TypeError(msg, creator, args, kwargs)

                def create_async(*_: P.args, **__: P.kwargs) -> typing.AsyncContextManager[T_co]:
                    return cm_async

                return True, create_async

            case cm_sync if cls._check_creator_is_context_manager(cm_sync):
                if args or kwargs:
                    msg = "ContextManager does not accept any arguments"
                    raise TypeError(msg, creator, args, kwargs)

                def create_sync(*_: P.args, **__: P.kwargs) -> typing.ContextManager[T_co]:
                    return cm_sync

                return False, create_sync

            case func_async if cls._check_creator_is_async_iterator_function(func_async):
                return True, contextlib.asynccontextmanager(func_async)

            case func_sync if cls._check_creator_is_iterator_function(func_sync):
                return False, contextlib.contextmanager(creator)

            case cm_async_func if cls._check_creator_is_async_context_manager_function(cm_async_func):
                return True, creator

            case cm_sync_func if cls._check_creator_is_context_manager_function(cm_sync_func):
                return False, cm_sync_func

            case _:
                # TODO(zerlok): suggest use TypeError instead, backward incompatible change. # noqa: TD003, FIX002
                msg = f"{type(resource).__name__} must be generator function"
                raise RuntimeError(msg)

    @classmethod
    def _check_creator_is_async_context_manager(
        cls,
        creator: ResourceCreator[P, T_co],
    ) -> typing.TypeGuard[typing.AsyncContextManager[T_co]]:
        return isinstance(creator, typing.AsyncContextManager)

    @classmethod
    def _check_creator_is_context_manager(
        cls,
        creator: ResourceCreator[P, T_co],
    ) -> typing.TypeGuard[typing.ContextManager[T_co]]:
        return isinstance(creator, typing.ContextManager)

    @classmethod
    def _check_creator_is_async_iterator_function(
        cls,
        creator: ResourceCreator[P, T_co],
    ) -> typing.TypeGuard[typing.Callable[P, typing.AsyncIterator[T_co]]]:
        return inspect.isasyncgenfunction(creator)

    @classmethod
    def _check_creator_is_iterator_function(
        cls,
        creator: ResourceCreator[P, T_co],
    ) -> typing.TypeGuard[typing.Callable[P, typing.Iterator[T_co]]]:
        return inspect.isgeneratorfunction(creator)

    @classmethod
    def _check_creator_is_async_context_manager_function(
        cls,
        creator: ResourceCreator[P, T_co],
    ) -> typing.TypeGuard[typing.Callable[P, typing.AsyncContextManager[T_co]]]:
        # NOTE: creator may be wrapped with `asynccontextmanager` decorator, but `inspect.signature` returns iterator
        # annotation in such cases (because of `functools.wraps`). Assuming that client code uses mypy, thus it's
        # impossible to receive inappropriate type here.
        returns = cls._get_creator_function_return_type(creator)
        return returns is not None and issubclass(returns, typing.AsyncContextManager | typing.AsyncIterator)

    @classmethod
    def _check_creator_is_context_manager_function(
        cls,
        creator: ResourceCreator[P, T_co],
    ) -> typing.TypeGuard[typing.Callable[P, typing.ContextManager[T_co]]]:
        # NOTE: creator may be wrapped with `contextmanager` decorator, but `inspect.signature` returns iterator
        # annotation in such cases (because of `functools.wraps`). Assuming that client code uses mypy, thus it's
        # impossible to receive inappropriate type here.
        returns = cls._get_creator_function_return_type(creator)
        return returns is not None and issubclass(returns, typing.ContextManager | typing.Iterator)

    @classmethod
    def _get_creator_function_return_type(
        cls,
        creator: ResourceCreator[P, T_co],
    ) -> type | None:
        if not inspect.isfunction(creator):
            return None

        return_annotation = inspect.signature(creator).return_annotation
        returns = typing.get_origin(return_annotation) or return_annotation

        return returns if isinstance(returns, type) else None


class AbstractFactory(AbstractProvider[T_co], abc.ABC):
    """Abstract Factory Class."""

    @property
    def provider(self) -> typing.Callable[[], typing.Coroutine[typing.Any, typing.Any, T_co]]:
        return self.async_resolve

    @property
    def sync_provider(self) -> typing.Callable[[], T_co]:
        return self.sync_resolve


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
