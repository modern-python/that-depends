import asyncio
import threading
import typing

from typing_extensions import override

from that_depends.providers import AbstractProvider


T_co = typing.TypeVar("T_co", covariant=True)
P = typing.ParamSpec("P")


class ThreadLocalSingleton(AbstractProvider[T_co]):
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
        self._args: typing.Final[P.args] = args
        self._kwargs: typing.Final[P.kwargs] = kwargs

    @property
    def _instance(self) -> T_co | None:
        return getattr(self._thread_local, "instance", None)

    @_instance.setter
    def _instance(self, value: T_co | None) -> None:
        self._thread_local.instance = value

    @override
    async def async_resolve(self) -> T_co:
        if self._override is not None:
            return typing.cast(T_co, self._override)

        async with self._asyncio_lock:
            if self._instance is not None:
                return self._instance

            self._instance = self._factory(
                *[await x.async_resolve() if isinstance(x, AbstractProvider) else x for x in self._args],
                **{
                    k: await v.async_resolve() if isinstance(v, AbstractProvider) else v
                    for k, v in self._kwargs.items()
                },
            )
            return self._instance

    @override
    def sync_resolve(self) -> T_co:
        if self._override is not None:
            return typing.cast(T_co, self._override)

        if self._instance is not None:
            return self._instance

        self._instance = self._factory(
            *[x.sync_resolve() if isinstance(x, AbstractProvider) else x for x in self._args],
            **{k: v.sync_resolve() if isinstance(v, AbstractProvider) else v for k, v in self._kwargs.items()},
        )
        return self._instance

    def tear_down(self) -> None:
        """Reset the thread-local instance.

        After calling this method, subsequent calls to `sync_resolve` on the
        same thread will produce a new instance.
        """
        if self._instance is not None:
            self._instance = None
