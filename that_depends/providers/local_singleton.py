import asyncio
import threading
import typing

from typing_extensions import override

from that_depends.providers import AbstractProvider
from that_depends.providers.mixin import ProviderWithArguments, SupportsTeardown


T_co = typing.TypeVar("T_co", covariant=True)
P = typing.ParamSpec("P")


class ThreadLocalSingleton(ProviderWithArguments, SupportsTeardown, AbstractProvider[T_co]):
    """Creates a new instance for each thread using a thread-local store.

    This provider ensures that each thread gets its own instance, which is
    created via the specified factory function. Once created, the instance is
    cached for future injections within the same thread.

    Example:
        ```python
        def factory():
            return random.randint(1, 100)

        singleton = ThreadLocalSingleton(factory)

        # Same thread, same instance
        instance1 = singleton.sync_resolve()
        instance2 = singleton.sync_resolve()

        def thread_task():
            return singleton.sync_resolve()

        threads = [threading.Thread(target=thread_task) for i in range(10)]
        for thread in threads:
            thread.start() # Each thread will get a different instance
        ```

    """

    def __init__(self, factory: typing.Callable[P, T_co], *args: P.args, **kwargs: P.kwargs) -> None:
        """Initialize the ThreadLocalSingleton provider.

        Args:
            factory: A callable that returns a new instance of the dependency.
            *args: Positional arguments to pass to the factory.
            **kwargs: Keyword arguments to pass to the factory

        """
        super().__init__()
        self._factory: typing.Final = factory
        self._thread_local = threading.local()
        self._asyncio_lock = asyncio.Lock()
        self._args: typing.Final = args
        self._kwargs: typing.Final = kwargs

    def _register_arguments(self) -> None:
        self._register(self._args)
        self._register(self._kwargs.values())

    def _deregister_arguments(self) -> None:
        self._deregister(self._args)
        self._deregister(self._kwargs.values())

    @property
    def _instance(self) -> T_co | None:
        return getattr(self._thread_local, "instance", None)

    @_instance.setter
    def _instance(self, value: T_co | None) -> None:
        self._thread_local.instance = value

    @override
    async def resolve(self) -> T_co:
        if self._override is not None:
            return typing.cast(T_co, self._override)

        async with self._asyncio_lock:
            if self._instance is not None:
                return self._instance

            self._register_arguments()

            self._instance = self._factory(
                *[await x.resolve() if isinstance(x, AbstractProvider) else x for x in self._args],  # type: ignore[arg-type]
                **{  # type: ignore[arg-type]
                    k: await v.resolve() if isinstance(v, AbstractProvider) else v for k, v in self._kwargs.items()
                },
            )
            return self._instance

    @override
    def resolve_sync(self) -> T_co:
        if self._override is not None:
            return typing.cast(T_co, self._override)

        if self._instance is not None:
            return self._instance

        self._register_arguments()

        self._instance = self._factory(
            *[x.resolve_sync() if isinstance(x, AbstractProvider) else x for x in self._args],  # type: ignore[arg-type]
            **{k: v.resolve_sync() if isinstance(v, AbstractProvider) else v for k, v in self._kwargs.items()},  # type: ignore[arg-type]
        )
        return self._instance

    @override
    def tear_down_sync(self, propagate: bool = True, raise_on_async: bool = True) -> None:
        if self._instance is not None:
            self._instance = None
        self._deregister_arguments()
        if propagate:
            self._tear_down_children_sync(propagate=propagate, raise_on_async=raise_on_async)

    @override
    async def tear_down(self, propagate: bool = True) -> None:
        """Reset the thread-local instance.

        After calling this method, subsequent calls to `sync_resolve` on the
        same thread will produce a new instance.
        """
        if self._instance is not None:
            self._instance = None
        self._deregister_arguments()
        if propagate:
            await self._tear_down_children()
