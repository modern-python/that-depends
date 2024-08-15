import contextlib
import logging
import typing
import warnings
from contextvars import ContextVar

from that_depends.providers.base import ResourceContext
from that_depends.providers.resources import Resource


T = typing.TypeVar("T")
P = typing.ParamSpec("P")
context_var: ContextVar[dict[str, ResourceContext[typing.Any]]] = ContextVar("context")
logger = logging.getLogger(__name__)


@contextlib.asynccontextmanager
async def container_context() -> typing.AsyncIterator[None]:
    token = context_var.set({})
    try:
        yield
    finally:
        for provider in reversed(context_var.get().values()):
            await provider.tear_down()

        context_var.reset(token)


def _get_context() -> dict[str, ResourceContext[typing.Any]]:
    try:
        return context_var.get()
    except LookupError as exc:
        msg = "Context is not set. Use container_context"
        raise RuntimeError(msg) from exc


class ContextResource(Resource[T]):
    def _fetch_context(self) -> ResourceContext[T] | None:
        return _get_context().get(self._internal_name)

    def _set_context(self, context: ResourceContext[T] | None) -> None:
        context_obj = _get_context()
        if context:
            context_obj[self._internal_name] = context

    async def tear_down(self) -> None:
        pass


class AsyncContextResource(ContextResource[T]):
    def __init__(
        self,
        creator: typing.Callable[P, typing.AsyncIterator[T]],
        *args: P.args,
        **kwargs: P.kwargs,
    ) -> None:
        warnings.warn("AsyncContextResource is deprecated, use ContextResource instead", RuntimeWarning, stacklevel=1)
        super().__init__(creator, *args, **kwargs)
