import functools
import inspect
import re
import typing
import warnings
from contextlib import AsyncExitStack
from types import TracebackType

from typing_extensions import Self

from that_depends.container import BaseContainer
from that_depends.exceptions import TypeNotBoundError
from that_depends.meta import BaseContainerMeta
from that_depends.providers import AbstractProvider
from that_depends.providers.context_resources import ContextScope, ContextScopes, container_context


class ContextProviderError(Exception):
    """Exception raised when a context provider is used where it is not expected."""


P = typing.ParamSpec("P")
T = typing.TypeVar("T")
_STRING_PROVIDER_PATTERN = re.compile(r"^([^.]+)\.([^.]+)(?:\.(.+))?$")
_INJECTION_WARNING_MESSAGE: typing.Final[str] = "Expected injection, but nothing found. Remove @inject decorator."
_PROVIDE_MESSAGE: typing.Final[str] = (
    "Use @Container.inject or @inject(container=Container) if you wish to use Provide()"
)


class _DirectInjectionParameter(typing.NamedTuple):
    argument_index: int
    field_name: str
    provider: AbstractProvider[typing.Any]
    scope_context_init_order: tuple[AbstractProvider[typing.Any], ...]


class _StringInjectionParameter(typing.NamedTuple):
    argument_index: int
    field_name: str
    definition: "StringProviderDefinition"


class _TypedInjectionParameter(typing.NamedTuple):
    argument_index: int
    field_name: str
    annotation: type[typing.Any]


class _InjectionPlan(typing.NamedTuple):
    direct_parameters: tuple[_DirectInjectionParameter, ...]
    string_parameters: tuple[_StringInjectionParameter, ...]
    typed_parameters: tuple[_TypedInjectionParameter, ...]


class _SyncInjectionStack:
    __slots__ = ("_exit_states",)

    def __init__(self) -> None:
        self._exit_states: list[_SupportsClose] = []

    def __enter__(self) -> Self:
        return self

    def __exit__(
        self,
        exc_type: type[BaseException] | None,
        exc_value: BaseException | None,
        traceback: TracebackType | None,
    ) -> typing.Literal[False]:
        _ = exc_type, exc_value, traceback
        while self._exit_states:
            self._exit_states.pop().close()
        return False

    def enter_context(self, context_manager: typing.ContextManager[T]) -> T:
        value = context_manager.__enter__()
        self._exit_states.append(_ContextManagerExitState(context_manager))
        return value

    def push_exit_state(self, exit_state: "_SupportsClose") -> None:
        self._exit_states.append(exit_state)


class _SupportsClose(typing.Protocol):
    def close(self) -> None: ...


class _ContextManagerExitState:
    __slots__ = ("_context_manager",)

    def __init__(self, context_manager: typing.ContextManager[typing.Any]) -> None:
        self._context_manager = context_manager

    def close(self) -> None:
        self._context_manager.__exit__(None, None, None)


@functools.cache
def _build_injection_plan(func: typing.Callable[..., typing.Any]) -> _InjectionPlan:
    direct_parameters: list[_DirectInjectionParameter] = []
    string_parameters: list[_StringInjectionParameter] = []
    typed_parameters: list[_TypedInjectionParameter] = []
    for index, (field_name, param) in enumerate(inspect.signature(func).parameters.items()):
        default = param.default
        if isinstance(default, StringProviderDefinition):
            string_parameters.append(_StringInjectionParameter(index, field_name, default))
        elif isinstance(default, AbstractProvider):
            direct_parameters.append(
                _DirectInjectionParameter(
                    index,
                    field_name,
                    default,
                    default._get_scope_context_init_order(),  # noqa: SLF001
                )
            )
        elif isinstance(default, _Provide):
            typed_parameters.append(
                _TypedInjectionParameter(
                    index,
                    field_name,
                    typing.cast(type[typing.Any], param.annotation),
                )
            )
    return _InjectionPlan(
        direct_parameters=tuple(direct_parameters),
        string_parameters=tuple(string_parameters),
        typed_parameters=tuple(typed_parameters),
    )


@typing.overload
def inject(func: typing.Callable[P, T]) -> typing.Callable[P, T]: ...


@typing.overload
def inject(
    *,
    scope: ContextScope | None = ContextScopes.INJECT,
    container: BaseContainerMeta | None = None,
    enter_scope: bool = False,
) -> typing.Callable[[typing.Callable[P, T]], typing.Callable[P, T]]: ...


def inject(  # noqa: C901
    func: typing.Callable[P, T] | None = None,
    scope: ContextScope | None = ContextScopes.INJECT,
    container: BaseContainerMeta | None = None,
    enter_scope: bool = False,
) -> typing.Callable[P, T] | typing.Callable[[typing.Callable[P, T]], typing.Callable[P, T]]:
    """Mark a function for dependency injection.

    Args:
        func: function or generator function to be wrapped.
        scope: scope to initialize ContextResources for.
        container: container from which to resolve dependencies marked with `Provide()`.
        enter_scope: enter the provided scope.

    Returns:
        wrapped function.

    """
    if scope == ContextScopes.ANY:
        msg = f"{scope} is not allowed in inject decorator."
        raise ValueError(msg)
    if scope is None and enter_scope:
        msg = "enter_scope cannot be used with scope=None."
        raise ValueError(msg)

    def _inject(
        func: typing.Callable[P, T],
    ) -> typing.Callable[P, T]:
        if inspect.isasyncgenfunction(func):
            if enter_scope:
                msg = "enter_scope cannot be used with async generator functions."
                raise ValueError(msg)
            return typing.cast(typing.Callable[P, T], _inject_to_async_gen(func))
        if inspect.isgeneratorfunction(func):
            if enter_scope:
                msg = "enter_scope cannot be used with generator functions."
                raise ValueError(msg)
            return typing.cast(typing.Callable[P, T], _inject_to_sync_gen(func))
        if inspect.iscoroutinefunction(func):
            return typing.cast(typing.Callable[P, T], _inject_to_async(func))

        return _inject_to_sync(func)

    def _inject_to_sync_gen(
        gen: typing.Callable[P, typing.Generator[T, typing.Any, typing.Any]],
    ) -> typing.Callable[P, typing.Generator[T, typing.Any, typing.Any]]:
        plan = _build_injection_plan(gen)

        @functools.wraps(gen)
        def inner(*args: P.args, **kwargs: P.kwargs) -> typing.Generator[T, typing.Any, typing.Any]:
            injected, kwargs = _resolve_arguments_sync(plan, scope, container, None, *args, **kwargs)  # type: ignore[assignment]

            if not injected:
                warnings.warn(_INJECTION_WARNING_MESSAGE, RuntimeWarning, stacklevel=2)

            g = gen(*args, **kwargs)
            result = yield from g
            return result

        return inner

    def _inject_to_async_gen(
        gen: typing.Callable[P, typing.AsyncGenerator[T, typing.Any]],
    ) -> typing.Callable[P, typing.AsyncGenerator[T, typing.Any]]:
        plan = _build_injection_plan(gen)

        @functools.wraps(gen)
        async def inner(*args: P.args, **kwargs: P.kwargs) -> typing.AsyncGenerator[T, typing.Any]:
            injected, kwargs = await _resolve_arguments_async(plan, scope, container, None, *args, **kwargs)  # type: ignore[assignment]

            if not injected:
                warnings.warn(_INJECTION_WARNING_MESSAGE, RuntimeWarning, stacklevel=1)

            async for item in gen(*args, **kwargs):
                yield item

        return inner

    def _inject_to_async(
        func: typing.Callable[P, typing.Coroutine[typing.Any, typing.Any, T]],
    ) -> typing.Callable[P, typing.Coroutine[typing.Any, typing.Any, T]]:
        plan = _build_injection_plan(func)

        @functools.wraps(func)
        async def inner(*args: P.args, **kwargs: P.kwargs) -> T:
            if enter_scope:
                async with container_context(scope=scope):
                    return await _resolve_async(func, plan, None, container, *args, **kwargs)
            else:
                return await _resolve_async(func, plan, scope, container, *args, **kwargs)

        return inner

    def _inject_to_sync(
        func: typing.Callable[P, T],
    ) -> typing.Callable[P, T]:
        plan = _build_injection_plan(func)

        @functools.wraps(func)
        def inner(*args: P.args, **kwargs: P.kwargs) -> T:
            if enter_scope:
                with container_context(scope=scope):
                    return _resolve_sync(func, plan, None, container, *args, **kwargs)
            else:
                return _resolve_sync(func, plan, scope, container, *args, **kwargs)

        return inner

    if func is None:
        return _inject
    return _inject(func)


async def _resolve_arguments_async(
    plan: _InjectionPlan,
    scope: ContextScope | None,
    container: BaseContainerMeta | None,
    stack: AsyncExitStack | None,
    *args: typing.Any,  # noqa: ANN401
    **kwargs: typing.Any,  # noqa: ANN401
) -> tuple[bool, dict[str, typing.Any]]:
    if not _plan_has_injected_parameters(plan):
        return False, kwargs

    context_providers: set[AbstractProvider[typing.Any]] = set()
    for direct_parameter in plan.direct_parameters:
        if _is_argument_provided(direct_parameter.argument_index, direct_parameter.field_name, args, kwargs):
            continue

        if direct_parameter.scope_context_init_order:
            await _setup_scope_contexts_async(
                direct_parameter.scope_context_init_order,
                scope,
                stack,
                context_providers,
            )
        kwargs[direct_parameter.field_name] = await direct_parameter.provider.resolve()

    for string_parameter in plan.string_parameters:
        if _is_argument_provided(string_parameter.argument_index, string_parameter.field_name, args, kwargs):
            continue

        kwargs[string_parameter.field_name] = await _resolve_provider_with_scope_async(
            string_parameter.definition.provider,
            scope,
            stack,
            context_providers,
        )

    for typed_parameter in plan.typed_parameters:
        if _is_argument_provided(typed_parameter.argument_index, typed_parameter.field_name, args, kwargs):
            continue

        provider = _resolve_typed_provider(typed_parameter.annotation, container)
        kwargs[typed_parameter.field_name] = await _resolve_provider_with_scope_async(
            provider,
            scope,
            stack,
            context_providers,
        )
    return True, kwargs


def _resolve_arguments_sync(
    plan: _InjectionPlan,
    scope: ContextScope | None,
    container: BaseContainerMeta | None,
    stack: _SyncInjectionStack | None,
    *args: typing.Any,  # noqa: ANN401
    **kwargs: typing.Any,  # noqa: ANN401
) -> tuple[bool, dict[str, typing.Any]]:
    if not _plan_has_injected_parameters(plan):
        return False, kwargs

    context_providers: set[AbstractProvider[typing.Any]] = set()
    for direct_parameter in plan.direct_parameters:
        if _is_argument_provided(direct_parameter.argument_index, direct_parameter.field_name, args, kwargs):
            continue

        if direct_parameter.scope_context_init_order:
            _setup_scope_contexts_sync(
                direct_parameter.scope_context_init_order,
                scope,
                stack,
                context_providers,
            )
        kwargs[direct_parameter.field_name] = direct_parameter.provider.resolve_sync()

    for string_parameter in plan.string_parameters:
        if _is_argument_provided(string_parameter.argument_index, string_parameter.field_name, args, kwargs):
            continue

        kwargs[string_parameter.field_name] = _resolve_provider_with_scope_sync(
            string_parameter.definition.provider,
            scope,
            stack,
            context_providers,
        )

    for typed_parameter in plan.typed_parameters:
        if _is_argument_provided(typed_parameter.argument_index, typed_parameter.field_name, args, kwargs):
            continue

        provider = _resolve_typed_provider(typed_parameter.annotation, container)
        kwargs[typed_parameter.field_name] = _resolve_provider_with_scope_sync(
            provider,
            scope,
            stack,
            context_providers,
        )

    return True, kwargs


def _plan_has_injected_parameters(plan: _InjectionPlan) -> bool:
    return bool(plan.direct_parameters or plan.string_parameters or plan.typed_parameters)


def _is_argument_provided(
    argument_index: int,
    field_name: str,
    args: tuple[typing.Any, ...],
    kwargs: dict[str, typing.Any],
) -> bool:
    return argument_index < len(args) or field_name in kwargs


def _resolve_typed_provider(
    annotation: type[typing.Any],
    container: BaseContainerMeta | None,
) -> AbstractProvider[typing.Any]:
    if container is None:
        raise RuntimeError(_PROVIDE_MESSAGE)
    try:
        return container.get_provider_for_type(annotation)
    except TypeNotBoundError as e:
        msg = f"Type {annotation} is not bound to a provider."
        raise RuntimeError(msg) from e


def _resolve_sync(
    func: typing.Callable[P, T],
    plan: _InjectionPlan,
    scope: ContextScope | None,
    container: BaseContainerMeta | None = None,
    *args: P.args,
    **kwargs: P.kwargs,
) -> T:
    if scope is None:
        injected, kwargs = _resolve_arguments_sync(plan, scope, container, None, *args, **kwargs)  # type: ignore[assignment]
        if not injected:
            warnings.warn(_INJECTION_WARNING_MESSAGE, RuntimeWarning, stacklevel=3)

        return func(*args, **kwargs)

    with _SyncInjectionStack() as stack:
        injected, kwargs = _resolve_arguments_sync(plan, scope, container, stack, *args, **kwargs)  # type: ignore[assignment]

        if not injected:
            warnings.warn(_INJECTION_WARNING_MESSAGE, RuntimeWarning, stacklevel=3)

        return func(*args, **kwargs)

    raise RuntimeError  # pragma: no cover # to prevent mypy issue


async def _resolve_async(
    func: typing.Callable[P, typing.Coroutine[typing.Any, typing.Any, T]],
    plan: _InjectionPlan,
    scope: ContextScope | None,
    container: BaseContainerMeta | None = None,
    *args: P.args,
    **kwargs: P.kwargs,
) -> T:
    async with AsyncExitStack() as stack:
        injected, kwargs = await _resolve_arguments_async(plan, scope, container, stack, *args, **kwargs)  # type: ignore[assignment]
        if not injected:
            warnings.warn(_INJECTION_WARNING_MESSAGE, RuntimeWarning, stacklevel=1)

        return await func(*args, **kwargs)

    raise RuntimeError  # pragma: no cover # to prevent mypy issue


async def _resolve_provider_with_scope_async(
    provider: AbstractProvider[T],
    scope: ContextScope | None,
    stack: AsyncExitStack | None,
    providers: set[AbstractProvider[typing.Any]],
) -> T:
    """Resolve a provider with given scope and stack.

    Use `stack=None` to ensure ContextResource providers are not allowed.

    Args:
        provider: provider to resolve.
        scope: scope to resolve provider in.
        stack: stack to use for context resources.
        providers: providers traversed.

    Returns:
        resolved value for the provider.

    Raises:
        ContextProviderError: if the stack is None.

    """
    scope_context_init_order = provider._get_scope_context_init_order()  # noqa: SLF001
    if scope_context_init_order:
        await _setup_scope_contexts_async(scope_context_init_order, scope, stack, providers)
    return await provider.resolve()


async def _setup_scope_contexts_async(
    scope_init_order: tuple[AbstractProvider[typing.Any], ...],
    scope: ContextScope | None,
    stack: AsyncExitStack | None,
    providers: set[AbstractProvider[typing.Any]],
) -> None:
    if not scope:
        return
    for provider in scope_init_order:
        if provider in providers:
            continue
        providers.add(provider)
        provider_scope = provider._scope  # noqa: SLF001
        if provider_scope is ContextScopes.ANY or provider_scope is scope:
            if stack is None:
                msg = (
                    f"No stack exists, cannot initialize context for {provider} using scope {scope}.\n"
                    f"Note: @inject cannot initialize context for ContextResources when wrapping a generator."
                )
                raise ContextProviderError(msg)
            await stack.enter_async_context(provider.context_async(force=True))


def _resolve_provider_with_scope_sync(
    provider: AbstractProvider[T],
    scope: ContextScope | None,
    stack: _SyncInjectionStack | None,
    providers: set[AbstractProvider[typing.Any]],
) -> T:
    scope_context_init_order = provider._get_scope_context_init_order()  # noqa: SLF001
    if scope_context_init_order:
        _setup_scope_contexts_sync(scope_context_init_order, scope, stack, providers)
    return provider.resolve_sync()


def _setup_scope_contexts_sync(
    scope_init_order: tuple[AbstractProvider[typing.Any], ...],
    scope: ContextScope | None,
    stack: _SyncInjectionStack | None,
    providers: set[AbstractProvider[typing.Any]],
) -> None:
    if not scope:
        return
    for provider in scope_init_order:
        if provider in providers:
            continue
        providers.add(provider)
        provider_scope = provider._scope  # noqa: SLF001
        if provider_scope is ContextScopes.ANY or provider_scope is scope:
            if stack is None:
                msg = (
                    f"No stack exists, cannot initialize context for {provider} using scope {scope}.\n"
                    f"Note: @inject cannot initialize context for ContextResources when wrapping a generator."
                )
                raise ContextProviderError(msg)
            _, exit_state = provider._enter_injection_context_sync(force=True)  # noqa: SLF001
            stack.push_exit_state(exit_state)


class StringProviderDefinition:
    """Provider definition from a string."""

    def __init__(self, definition: str) -> None:
        """Initialize the provider definition.

        Args:
            definition: provider definition in the format container.provider[.attr1.attr2...].

        """
        self._definition = definition
        self._container_name, self._provider_name, self._attrs = self._validate_and_extract_provider_definition()

    def _validate_and_extract_provider_definition(self) -> tuple[str, str, list[str]]:
        match = re.match(_STRING_PROVIDER_PATTERN, self._definition)
        if match:
            container_name = match.group(1)
            provider_name = match.group(2)
            attrs = match.group(3).split(".") if match.group(3) else []
            return container_name, provider_name, attrs
        msg = f"Invalid provider definition: {self._definition}"
        raise ValueError(msg)

    def _get_container_by_name(self) -> type["BaseContainer"]:
        containers_in_scope = BaseContainerMeta.get_instances()
        try:
            return containers_in_scope[self._container_name]
        except KeyError as e:
            msg = f"Container {self._container_name} not found in scope!"
            raise ValueError(msg) from e

    def _get_provider_by_name(self) -> AbstractProvider[typing.Any]:
        container = self._get_container_by_name()
        try:
            provider = container.get_providers()[self._provider_name]
        except KeyError as e:
            msg = f"Provider {self._provider_name} not found in container {self._container_name}"
            raise ValueError(msg) from e
        for attr in self._attrs:
            provider = getattr(provider, attr)
        return provider

    @property
    def provider(self) -> AbstractProvider[typing.Any]:
        """Get the provider instance."""
        return self._get_provider_by_name()


class _Provide:
    def __getitem__(self, provider: AbstractProvider[T] | str) -> T | typing.Any:  # noqa: ANN401
        if isinstance(provider, str):
            return StringProviderDefinition(provider)  # will be resolved later
        return typing.cast(T, provider)

    def __call__(self) -> typing.Any:  # noqa: ANN401
        """Marker for automatic dependency injection."""
        return self


Provide: typing.Final[_Provide] = _Provide()
