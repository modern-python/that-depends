import abc


class SupportsTeardown(abc.ABC):
    """Interface for objects that support teardown."""

    @abc.abstractmethod
    async def tear_down(self) -> None:
        """Perform any necessary cleanup operations.

        This method is called when the object is no longer needed.
        """

    @abc.abstractmethod
    def sync_tear_down(self) -> None:
        """Perform any necessary cleanup operations.

        This method is called when the object is no longer needed.
        """
