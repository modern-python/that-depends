import abc


class CannotTearDownSyncError(RuntimeError):
    """Raised when attempting to tear down an async resource in sync mode."""


class SupportsTeardown(abc.ABC):
    """Interface for objects that support teardown."""

    @abc.abstractmethod
    async def tear_down(self, propagate: bool = True) -> None:
        """Perform any necessary cleanup operations.

        This method is called when the object is no longer needed.
        """

    @abc.abstractmethod
    def tear_down_sync(self, propagate: bool = True, raise_on_async: bool = True) -> None:
        """Perform any necessary cleanup operations.

        This method is called when the object is no longer needed.
        """


class ProviderWithArguments(abc.ABC):
    """Interface for providers that require arguments."""

    __slots__ = ("_arguments_registered",)

    def __init__(self) -> None:
        """Initialize provider argument registration state."""
        super().__init__()
        self._arguments_registered = False

    def _mark_arguments_registered(self) -> bool:
        if self._arguments_registered:
            return False
        self._arguments_registered = True
        return True

    def _reset_arguments_registration(self) -> None:
        self._arguments_registered = False

    @abc.abstractmethod
    def _register_arguments(self) -> None:
        """Register arguments for the provider."""

    @abc.abstractmethod
    def _deregister_arguments(self) -> None:
        """Deregister arguments for the provider."""
