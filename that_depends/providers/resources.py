import typing
import warnings

from that_depends.providers.base import AbstractResource, ResourceContext


T = typing.TypeVar("T")
P = typing.ParamSpec("P")


class Resource(AbstractResource[T]):
    __slots__ = (
        "_is_async",
        "_creator",
        "_args",
        "_kwargs",
        "_override",
        "_context",
    )

    def __init__(
        self,
        creator: typing.Callable[P, typing.Iterator[T] | typing.AsyncIterator[T]],
        *args: P.args,
        **kwargs: P.kwargs,
    ) -> None:
        super().__init__(creator, *args, **kwargs)
        self._context: ResourceContext[T] = ResourceContext()

    def _fetch_context(self) -> ResourceContext[T]:
        return self._context

    async def tear_down(self) -> None:
        await self._fetch_context().tear_down()


class AsyncResource(Resource[T]):
    def __init__(
        self,
        creator: typing.Callable[P, typing.AsyncIterator[T]],
        *args: P.args,
        **kwargs: P.kwargs,
    ) -> None:
        warnings.warn("AsyncResource is deprecated, use Resource instead", RuntimeWarning, stacklevel=1)
        super().__init__(creator, *args, **kwargs)
