import typing

from that_depends.entities.resource_context import ResourceContext
from that_depends.providers.base import AbstractResource, ResourceCreatorType


T_co = typing.TypeVar("T_co", covariant=True)
P = typing.ParamSpec("P")


class Resource(AbstractResource[T_co]):
    """Provides a resource that is resolved once and cached for future usage.

    Unlike a singleton, this provider includes finalization logic and can be
    used with a generator or async generator to manage resource lifecycle.
    It also supports usage with `typing.ContextManager` or `typing.AsyncContextManager`.
    Threading and asyncio concurrency are supported, ensuring only one instance
    is created regardless of concurrent resolves.

    Example:
        ```python
        async def create_async_resource():
            try:
                yield "async resource"
            finally:
                # Finalize resource
                pass

        class MyContainer:
            async_resource = Resource(create_async_resource)

        async def main():
            async_resource_instance = await MyContainer.async_resource.async_resolve()
            await MyContainer.async_resource.tear_down()
        ```

    """

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
        """Initialize the Resource provider with a callable for resource creation.

        The callable can be a generator or async generator that yields the resource
        (with optional teardown logic), or a context manager. Only one instance will be
        created and cached until explicitly torn down.

        Args:
            creator: The callable, generator, or context manager that creates the resource.
            *args: Positional arguments passed to the creator.
            **kwargs: Keyword arguments passed to the creator.

        Example:
            ```python
            def custom_creator(name: str):
                try:
                    yield f"Resource created for {name}"
                finally:
                    pass  # Teardown

            resource_provider = Resource(custom_creator, "example")
            instance = resource_provider.sync_resolve()
            resource_provider.tear_down()
            ```

        """
        super().__init__(creator, *args, **kwargs)
        self._context: typing.Final[ResourceContext[T_co]] = ResourceContext(is_async=self.is_async)

    def _fetch_context(self) -> ResourceContext[T_co]:
        return self._context

    async def tear_down(self) -> None:
        """Tear down the resource if it has been created.

        If the resource was never resolved, or was already torn down,
        calling this method has no effect.

        Example:
            ```python
            # Assuming my_provider was previously resolved
            await my_provider.tear_down()
            ```

        """
        await self._fetch_context().tear_down()
