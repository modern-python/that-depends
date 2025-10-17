import importlib
import re
import typing
from typing import Any, TypeVar, cast, overload

import typing_extensions

from that_depends import ContextScope
from that_depends.providers import AbstractProvider
from that_depends.providers.context_resources import CT, SupportsContext
from that_depends.providers.mixin import SupportsTeardown


T_co = TypeVar("T_co", covariant=True)

_IMPORT_STRING_REGEX = re.compile(r"^[a-zA-Z_][a-zA-Z0-9_]*(\.[a-zA-Z_][a-zA-Z0-9_]*)*$")


class LazyProvider(SupportsTeardown, SupportsContext[Any], AbstractProvider[Any]):
    """Lazily imports and provides a provider from a module."""

    @overload
    def __init__(self, *, module_string: str, provider_string: str) -> None: ...

    @overload
    def __init__(self, import_string: str, /) -> None: ...

    def __init__(
        self,
        import_string: str | None = None,
        module_string: str | None = None,
        provider_string: str | None = None,
    ) -> None:
        """Initialize a LazyProvider instance.

        Args:
            module_string: path to module to import from.
            provider_string: path to provider within module.
            import_string: path to provider including module and attributes.

        """
        super().__init__()
        if (import_string is not None) == (module_string is not None and provider_string is not None):
            msg = (
                "You must provide either import_string OR both module_string AND provider_string, "
                "but not both or neither."
            )
            raise ValueError(msg)

        self._module_string = module_string
        self._provider_string = provider_string
        self._import_string = import_string
        self._check_strings()
        self._provider: AbstractProvider[Any] | None = None

    @typing_extensions.override
    def get_scope(self) -> ContextScope | None:
        provider = self._get_provider()
        if isinstance(provider, SupportsContext):
            return provider.get_scope()
        msg = "Underlying provider does not support context scopes"
        raise NotImplementedError(msg)

    @typing_extensions.override
    def context_async(self, force: bool = False) -> typing.AsyncContextManager[CT]:
        provider = self._get_provider()
        if isinstance(provider, SupportsContext):
            return provider.context_async(force)
        msg = "Underlying provider does not support context management"
        raise NotImplementedError(msg)

    @typing_extensions.override
    def context_sync(self, force: bool = False) -> typing.ContextManager[CT]:
        provider = self._get_provider()
        if isinstance(provider, SupportsContext):
            return provider.context_sync(force)
        msg = "Underlying provider does not support context management"
        raise NotImplementedError(msg)

    @typing_extensions.override
    def supports_context_sync(self) -> bool:
        provider = self._get_provider()
        return isinstance(provider, SupportsContext) and provider.supports_context_sync()

    @typing_extensions.override
    async def tear_down(self, propagate: bool = True) -> None:
        provider = self._get_provider()
        if isinstance(provider, SupportsTeardown):
            await provider.tear_down(propagate=propagate)
        else:
            msg = "Underlying provider does not support tear down."
            raise NotImplementedError(msg)

    @typing_extensions.override
    def tear_down_sync(self, propagate: bool = True, raise_on_async: bool = True) -> None:
        provider = self._get_provider()
        if isinstance(provider, SupportsTeardown):
            provider.tear_down_sync(propagate=propagate, raise_on_async=raise_on_async)
        else:
            msg = "Underlying provider does not support tear down."
            raise NotImplementedError(msg)

    def _check_strings(self) -> None:
        if self._import_string is not None and not _IMPORT_STRING_REGEX.match(self._import_string):
            msg = f"Invalid import_string '{self._import_string}'"
            raise ValueError(msg)
        if self._module_string is not None and not _IMPORT_STRING_REGEX.match(self._module_string):
            msg = f"Invalid module_string '{self._module_string}'"
            raise ValueError(msg)
        if self._provider_string is not None and not _IMPORT_STRING_REGEX.match(self._provider_string):
            msg = f"Invalid provider_string '{self._provider_string}'"
            raise ValueError(msg)

    def _get_provider(self) -> AbstractProvider[Any]:
        if self._provider:
            return self._provider
        if self._import_string is not None:
            parts = self._import_string.split(".")
            for i in range(len(parts), 0, -1):
                module_name = ".".join(parts[:i])
                try:
                    module = importlib.import_module(module_name)
                    attrs = parts[i:]
                    break
                except ImportError:
                    continue
            else:
                msg = f"Cannot import any module from '{self._import_string}'"
                raise ImportError(msg)
        else:
            if self._module_string is None or self._provider_string is None:
                msg = "Invalid state: module_string and provider_string must be set"
                raise RuntimeError(msg)
            module = importlib.import_module(self._module_string)
            attrs = self._provider_string.split(".")
        provider = module
        for attr in attrs:
            provider = getattr(provider, attr)
        self._provider = cast(AbstractProvider[Any], provider)
        return self._provider

    @typing_extensions.override
    async def resolve(self) -> Any:
        provider = self._get_provider()
        return await provider.resolve()

    @typing_extensions.override
    def resolve_sync(self) -> Any:
        provider = self._get_provider()
        return provider.resolve_sync()

    @typing_extensions.override
    def override_sync(
        self, mock: object, tear_down_children: bool = False, propagate: bool = True, raise_on_async: bool = False
    ) -> None:
        provider = self._get_provider()
        provider.override_sync(mock, tear_down_children, propagate, raise_on_async)

    @typing_extensions.override
    async def override(self, mock: object, tear_down_children: bool = False, propagate: bool = True) -> None:
        provider = self._get_provider()
        await provider.override(mock, tear_down_children, propagate)

    @typing_extensions.override
    async def reset_override(self, tear_down_children: bool = False, propagate: bool = True) -> None:
        provider = self._get_provider()
        await provider.reset_override(tear_down_children, propagate)

    @typing_extensions.override
    def reset_override_sync(
        self, tear_down_children: bool = False, propagate: bool = True, raise_on_async: bool = False
    ) -> None:
        provider = self._get_provider()
        provider.reset_override_sync(tear_down_children, propagate, raise_on_async)

    @typing_extensions.override
    def __getattr__(self, attr_name: str) -> typing.Any:
        provider = self._get_provider()
        return getattr(provider, attr_name)
