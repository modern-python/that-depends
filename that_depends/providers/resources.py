import typing
import warnings

from that_depends.providers.base import AbstractResource, ResourceContext


T_co = typing.TypeVar("T_co", covariant=True)
P = typing.ParamSpec("P")


class Resource(AbstractResource[T_co]):
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
        creator: typing.Callable[P, typing.Iterator[T_co] | typing.AsyncIterator[T_co]],
        *args: P.args,
        **kwargs: P.kwargs,
    ) -> None:
        super().__init__(creator, *args, **kwargs)
        self._context: typing.Final[ResourceContext[T_co]] = ResourceContext(is_async=self._is_async)

    def _fetch_context(self) -> ResourceContext[T_co]:
        return self._context

    async def tear_down(self) -> None:
        await self._fetch_context().tear_down()


class AsyncResource(Resource[T_co]):
    def __init__(
        self,
        creator: typing.Callable[P, typing.AsyncIterator[T_co]],
        *args: P.args,
        **kwargs: P.kwargs,
    ) -> None:
        warnings.warn("AsyncResource is deprecated, use Resource instead", RuntimeWarning, stacklevel=1)
        super().__init__(creator, *args, **kwargs)
