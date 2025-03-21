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
