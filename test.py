from that_depends import BaseContainer, providers


def creator_parent(val_1: int) -> int:
    """Test."""
    return val_1


def creator_with_args(val_1: int, val_2: int) -> int:
    """Test."""
    return val_1 + val_2


class Container(BaseContainer):
    """test."""

    parent_provider = providers.Singleton(creator_parent)
    child_provider = providers.Singleton(creator_with_args, val_2=5)


if __name__ == "__main__":
    Container.child_provider.resolve_sync(val_1=3)
