import asyncio
import contextlib
import threading
import typing
import warnings

from typing_extensions import override

from that_depends.providers.mixin import CannotTearDownSyncError, SupportsTeardown
from that_depends.utils import UNSET, Unset, is_set


T_co = typing.TypeVar("T_co", covariant=True)


class ResourceContext(SupportsTeardown, typing.Generic[T_co]):
    """Class to manage a resources' context."""

    __slots__ = "asyncio_lock", "context_stack", "instance", "is_async", "threading_lock"

    def __init__(self, is_async: bool) -> None:
        """Create a new ResourceContext instance.

        Args:
            is_async (bool): Whether the ResourceContext was created in
                an async context.
        For example within a ``async with container_context(Container): ...`` statement.

        """
        self.instance: T_co | Unset = UNSET
        self.asyncio_lock: typing.Final = asyncio.Lock()
        self.threading_lock: typing.Final = threading.Lock()
        self.context_stack: contextlib.AsyncExitStack | contextlib.ExitStack | Unset = UNSET
        self.is_async = is_async

    def set_context_state(
        self,
        *,
        instance: T_co | Unset = UNSET,
        context_stack: contextlib.AsyncExitStack | contextlib.ExitStack | Unset = UNSET,
    ) -> None:
        """Set the context state of the resource.

        Args:
            instance: instance.
            context_stack: stack.

        Returns:
            None

        """
        self.instance = instance
        self.context_stack = context_stack

    @staticmethod
    def is_context_stack_async(
        context_stack: object,
    ) -> typing.TypeGuard[contextlib.AsyncExitStack]:
        """Check if the context stack is an async context stack."""
        return isinstance(context_stack, contextlib.AsyncExitStack)

    @staticmethod
    def is_context_stack_sync(
        context_stack: object,
    ) -> typing.TypeGuard[contextlib.ExitStack]:
        """Check if the context stack is a sync context stack."""
        return isinstance(context_stack, contextlib.ExitStack)

    @override
    async def tear_down(self, propagate: bool = True) -> None:
        """Tear down the async context stack."""
        context_stack = self.context_stack
        if not is_set(context_stack):
            return

        if self.is_context_stack_async(context_stack):
            await context_stack.aclose()
        elif self.is_context_stack_sync(context_stack):
            context_stack.close()
        self.set_context_state(instance=UNSET, context_stack=UNSET)

    @override
    def tear_down_sync(self, propagate: bool = True, raise_on_async: bool = True) -> None:
        """Tear down the sync context stack."""
        context_stack = self.context_stack
        if not is_set(context_stack):
            return

        if self.is_context_stack_sync(context_stack):
            context_stack.close()
            self.set_context_state(instance=UNSET, context_stack=UNSET)
        elif self.is_context_stack_async(context_stack):
            msg = "Cannot tear down async context in sync mode"
            if raise_on_async:
                raise CannotTearDownSyncError(msg)
            warnings.warn(msg, RuntimeWarning, stacklevel=2)
