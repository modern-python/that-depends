import typing
from importlib.metadata import version
from types import TracebackType
from typing import Any, Final, Optional

from packaging.version import Version
from typing_extensions import deprecated, override

from that_depends import container_context
from that_depends.providers.context_resources import ContextScope, SupportsContext
from that_depends.utils import UNSET, Unset, is_set


_FASTSTREAM_MODULE_NAME: Final[str] = "faststream"
_FASTSTREAM_VERSION: Final[str] = version(_FASTSTREAM_MODULE_NAME)
if Version(_FASTSTREAM_VERSION) >= Version("0.6.0"):  # pragma: no cover
    from faststream import BaseMiddleware, ContextRepo
    from faststream._internal.types import AnyMsg

    class DIContextMiddleware(BaseMiddleware):
        """Initializes the container context for faststream brokers."""

        def __init__(
            self,
            *context_items: SupportsContext[Any],
            msg: AnyMsg | None = None,
            context: Optional["ContextRepo"] = None,
            global_context: dict[str, Any] | Unset = UNSET,
            scope: ContextScope | Unset = UNSET,
        ) -> None:
            """Initialize the container context middleware.

            Args:
                *context_items (SupportsContext[Any]): Context items to initialize.
                msg (Any): Message object.
                context (ContextRepo): Context repository.
                global_context (dict[str, Any] | Unset): Global context to initialize the container.
                scope (ContextScope | Unset): Context scope to initialize the container.

            """
            super().__init__(msg, context=context)  # type: ignore[arg-type]
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

        def __call__(self, msg: Any = None, **kwargs: Any) -> "DIContextMiddleware":  # noqa: ANN401
            """Create an instance of DIContextMiddleware.

            Args:
                msg (Any): Message object.
                **kwargs: Additional keyword arguments.

            Returns:
                DIContextMiddleware: A new instance of DIContextMiddleware.

            """
            context = kwargs.get("context")

            return DIContextMiddleware(
                *self._context_items,
                msg=msg,
                context=context,
                scope=self._scope,
                global_context=self._global_context,
            )
else:  # pragma: no cover
    from faststream import BaseMiddleware

    @deprecated("Will be removed with faststream v1")
    class DIContextMiddleware(BaseMiddleware):  # type: ignore[no-redef]
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
            super().__init__()  # type: ignore[call-arg]
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
