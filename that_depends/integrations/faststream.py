import typing
from types import TracebackType
from typing import Any, Optional

from faststream import BaseMiddleware
from typing_extensions import override

from that_depends import container_context
from that_depends.providers.context_resources import ContextScope, SupportsContext
from that_depends.utils import UNSET, Unset, is_set


class DIContextMiddleware(BaseMiddleware):
    """Initializes the container context for faststream brokers."""

    def __init__(
        self,
        *context_items: SupportsContext[Any],
        global_context: dict[str, Any] | Unset = UNSET,
        scope: ContextScope | Unset = UNSET,
    ) -> None:
        """Initialize the container context middleware.

        Args:
            *context_items (SupportsContext[Any]): Context items to initialize.
            global_context (dict[str, Any] | Unset): Global context to initialize the container.
            scope (ContextScope | Unset): Context scope to initialize the container.

        """
        super().__init__()
        self._context: container_context | None = None
        self._context_items = set(context_items)
        self._global_context = global_context
        self._scope = scope

    @override
    async def on_receive(self) -> None:
        self._context = container_context(
            *self._context_items,
            scope=self._scope if is_set(self._scope) else None,
            global_context=self._global_context if is_set(self._global_context) else None,
        )
        await self._context.__aenter__()

    @override
    async def after_processed(
        self,
        exc_type: type[BaseException] | None = None,
        exc_val: BaseException | None = None,
        exc_tb: Optional["TracebackType"] = None,
    ) -> bool | None:
        if self._context is not None:
            await self._context.__aexit__(exc_type, exc_val, exc_tb)
        return None

    def __call__(self, *args: typing.Any, **kwargs: typing.Any) -> "DIContextMiddleware":  # noqa: ARG002, ANN401
        """Create an instance of DIContextMiddleware."""
        return DIContextMiddleware(*self._context_items, scope=self._scope, global_context=self._global_context)
