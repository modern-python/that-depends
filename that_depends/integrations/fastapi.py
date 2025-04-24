import typing
from collections.abc import Callable
from inspect import signature

from fastapi import Depends, Request, Response
from fastapi.routing import APIRoute

from that_depends.injection import StringProviderDefinition
from that_depends.providers import AbstractProvider
from that_depends.providers.context_resources import ContextScope, SupportsContext, container_context


P = typing.ParamSpec("P")
T = typing.TypeVar("T")


def _adjust_fastapi_endpoint(endpoint: Callable[P, T]) -> Callable[P, T]:
    hints = typing.get_type_hints(endpoint, include_extras=True)
    sig = signature(endpoint)
    new_params = []
    for name, param in sig.parameters.items():
        if isinstance(param.default, AbstractProvider):
            hints[name] = Depends(param.default)
            new_params.append(param.replace(default=Depends(param.default)))
        elif isinstance(param.default, StringProviderDefinition):
            provider = param.default.provider
            hints[name] = Depends(provider)
            new_params.append(param.replace(default=Depends(provider)))
        else:
            new_params.append(param)
    endpoint.__annotations__ = hints
    endpoint.__signature__ = sig.replace(parameters=new_params)  # type: ignore[attr-defined]
    return endpoint


def create_fastapi_route_class(
    *context_items: SupportsContext[typing.Any],
    global_context: dict[str, typing.Any] | None = None,
    scope: ContextScope | None = None,
) -> type[APIRoute]:
    """Create a `that-depends` fastapi route class.

    Args:
        *context_items: Items to initialize context for.
        global_context: Global context to use.
        scope: scope to enter before on request.

    Returns:
        type[APIRoute]: A custom fastapi route class.

    """

    class _Route(APIRoute):
        """Custom that-depends router for FastAPI."""

        def __init__(self, path: str, endpoint: Callable[..., typing.Any], **kwargs: typing.Any) -> None:  # noqa: ANN401
            endpoint = _adjust_fastapi_endpoint(endpoint)
            super().__init__(path=path, endpoint=endpoint, **kwargs)

        def get_route_handler(self) -> Callable[[Request], typing.Coroutine[typing.Any, typing.Any, Response]]:
            original_route_handler = super().get_route_handler()

            async def _custom_route_handler(request: Request) -> Response:
                async with container_context(*context_items, global_context=global_context, scope=scope):
                    response: Response = await original_route_handler(request)
                    return response

            return _custom_route_handler if context_items or global_context or scope else original_route_handler

    return _Route
