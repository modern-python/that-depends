import asyncio
import contextlib
import inspect
import typing
import uuid
import warnings

from that_depends.providers.base import AbstractProvider, ResourceContext


T = typing.TypeVar("T")
P = typing.ParamSpec("P")


class Resource(AbstractProvider[T]):
    __slots__ = (
        "_is_async",
        "_creator",
        "_args",
        "_kwargs",
        "_override",
        "_resolving_lock",
        "_context",
        "_internal_name",
    )

    def __init__(
        self,
        creator: typing.Callable[P, typing.Iterator[T] | typing.AsyncIterator[T]],
        *args: P.args,
        **kwargs: P.kwargs,
    ) -> None:
        if inspect.isasyncgenfunction(creator):
            self._is_async = True
        elif inspect.isgeneratorfunction(creator):
            self._is_async = False
        else:
            msg = f"{type(self).__name__} must be generator function"
            raise RuntimeError(msg)

        self._creator = creator
        self._args = args
        self._kwargs = kwargs
        self._override = None
        self._resolving_lock = asyncio.Lock()
        self._context: ResourceContext[T] | None = None
        self._internal_name = f"{creator.__name__}-{uuid.uuid4()}"

    def _is_creator_async(
        self, _: typing.Callable[P, typing.Iterator[T] | typing.AsyncIterator[T]]
    ) -> typing.TypeGuard[typing.Callable[P, typing.AsyncIterator[T]]]:
        return self._is_async

    def _is_creator_sync(
        self, _: typing.Callable[P, typing.Iterator[T] | typing.AsyncIterator[T]]
    ) -> typing.TypeGuard[typing.Callable[P, typing.Iterator[T]]]:
        return not self._is_async

    def _fetch_context(self) -> ResourceContext[T] | None:
        return self._context

    def _set_context(self, context: ResourceContext[T] | None) -> None:
        self._context = context

    async def tear_down(self) -> None:
        context = self._fetch_context()
        if context:
            await context.tear_down()
            self._set_context(None)

    async def async_resolve(self) -> T:
        if self._override:
            return typing.cast(T, self._override)

        context = self._fetch_context()
        if context:
            return context.fetch_instance()

        # lock to prevent race condition while resolving
        async with self._resolving_lock:
            context_stack: contextlib.AsyncExitStack | contextlib.ExitStack
            if self._is_creator_async(self._creator):
                context_stack = contextlib.AsyncExitStack()
                instance = typing.cast(
                    T,
                    await context_stack.enter_async_context(
                        contextlib.asynccontextmanager(self._creator)(
                            *[await x() if isinstance(x, AbstractProvider) else x for x in self._args],
                            **{k: await v() if isinstance(v, AbstractProvider) else v for k, v in self._kwargs.items()},
                        ),
                    ),
                )
            elif self._is_creator_sync(self._creator):
                context_stack = contextlib.ExitStack()
                instance = context_stack.enter_context(
                    contextlib.contextmanager(self._creator)(
                        *[await x.async_resolve() if isinstance(x, AbstractProvider) else x for x in self._args],
                        **{
                            k: await v.async_resolve() if isinstance(v, AbstractProvider) else v
                            for k, v in self._kwargs.items()
                        },
                    ),
                )
            self._set_context(ResourceContext(context_stack=context_stack, instance=instance))
            return instance

    def sync_resolve(self) -> T:
        if self._override:
            return typing.cast(T, self._override)

        context = self._fetch_context()
        if context:
            return context.fetch_instance()

        if self._is_creator_async(self._creator):
            msg = "AsyncResource cannot be resolved synchronously"
            raise RuntimeError(msg)

        if self._is_creator_sync(self._creator):
            context_stack = contextlib.ExitStack()
            instance = context_stack.enter_context(
                contextlib.contextmanager(self._creator)(
                    *[x.sync_resolve() if isinstance(x, AbstractProvider) else x for x in self._args],
                    **{k: v.sync_resolve() if isinstance(v, AbstractProvider) else v for k, v in self._kwargs.items()},
                ),
            )
        self._set_context(ResourceContext(context_stack=context_stack, instance=instance))
        return instance


class AsyncResource(Resource[T]):
    def __init__(
        self,
        creator: typing.Callable[P, typing.AsyncIterator[T]],
        *args: P.args,
        **kwargs: P.kwargs,
    ) -> None:
        warnings.warn("AsyncResource is deprecated, use Resource instead", RuntimeWarning, stacklevel=1)
        super().__init__(creator, *args, **kwargs)
