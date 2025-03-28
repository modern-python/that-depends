import inspect

from that_depends import BaseContainer, Provide, inject, providers


def creator_parent(val_1: int) -> int:
    """Test."""
    assert val_1 == 5  # noqa: PLR2004
    return val_1


def creator_with_args(val_1: int, val_2: int) -> int:
    """Test."""
    return val_1 + val_2


class Container(BaseContainer):
    """test."""

    parent_provider = providers.Factory(creator_parent)
    child_provider = providers.Factory(creator_with_args, val_2=5)


@inject
def injected(val_1: int = 5, provided: int = Provide[Container.child_provider]) -> int:
    """Test."""
    assert isinstance(val_1, int)
    return provided


if __name__ == "__main__":
    sig = inspect.signature(creator_with_args)
    injected()
