import typing

from that_depends.entities.resource_context import ResourceContext
from that_depends.providers.base import AbstractResource, ResourceCreatorType


T_co = typing.TypeVar("T_co", covariant=True)
P = typing.ParamSpec("P")


class Resource(AbstractResource[T_co]):
    """Resource provider."""

    __slots__ = (
        "_args",
        "_context",
        "_creator",
        "_creator",
        "_is_async",
        "_kwargs",
        "_override",
        "is_async",
    )

    def __init__(
        self,
        creator: ResourceCreatorType[P, T_co],
        *args: P.args,
        **kwargs: P.kwargs,
    ) -> None:
        """Create a resource provider.

        Args:
            creator: iterator or context manager that will create the resource.
            *args: argument to pass to the creator.
            **kwargs: keyword arguments to pass to the creator.

        """
        super().__init__(creator, *args, **kwargs)
        self._context: typing.Final[ResourceContext[T_co]] = ResourceContext(is_async=self.is_async)

    def _fetch_context(self) -> ResourceContext[T_co]:
        return self._context

    async def tear_down(self) -> None:
        """Tear down the resource."""
        await self._fetch_context().tear_down()
