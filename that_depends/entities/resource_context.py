import asyncio
import contextlib
import threading
import typing


T_co = typing.TypeVar("T_co", covariant=True)


class ResourceContext(typing.Generic[T_co]):
    """Class to manage a resources' context."""

    __slots__ = "asyncio_lock", "context_stack", "instance", "is_async", "threading_lock"

    def __init__(self, is_async: bool) -> None:
        """Create a new ResourceContext instance.

        Args:
            is_async (bool): Whether the ResourceContext was created in
                an async context.
        For example within a ``async with container_context(): ...`` statement.

        """
        self.instance: T_co | None = None
        self.asyncio_lock: typing.Final = asyncio.Lock()
        self.threading_lock: typing.Final = threading.Lock()
        self.context_stack: contextlib.AsyncExitStack | contextlib.ExitStack | None = None
        self.is_async = is_async

    @staticmethod
    def is_context_stack_async(
        context_stack: contextlib.AsyncExitStack | contextlib.ExitStack | None,
    ) -> typing.TypeGuard[contextlib.AsyncExitStack]:
        """Check if the context stack is an async context stack."""
        return isinstance(context_stack, contextlib.AsyncExitStack)

    @staticmethod
    def is_context_stack_sync(
        context_stack: contextlib.AsyncExitStack | contextlib.ExitStack,
    ) -> typing.TypeGuard[contextlib.ExitStack]:
        """Check if the context stack is a sync context stack."""
        return isinstance(context_stack, contextlib.ExitStack)

    async def tear_down(self) -> None:
        """Tear down the async context stack."""
        if self.context_stack is None:
            return

        if self.is_context_stack_async(self.context_stack):
            await self.context_stack.aclose()
        elif self.is_context_stack_sync(self.context_stack):
            self.context_stack.close()
        self.context_stack = None
        self.instance = None

    def sync_tear_down(self) -> None:
        """Tear down the sync context stack."""
        if self.context_stack is None:
            return

        if self.is_context_stack_sync(self.context_stack):
            self.context_stack.close()
            self.context_stack = None
            self.instance = None
        elif self.is_context_stack_async(self.context_stack):
            msg = "Cannot tear down async context in sync mode"
            raise RuntimeError(msg)
