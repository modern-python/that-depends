from that_depends import BaseContainer, container_context, providers
from that_depends.meta import BaseContainerMeta


class Container(BaseContainer):
    """Container for the application."""

    alias = "TEXT"
    default_scope = None

    resource = providers.Factory(lambda: 42)


def main() -> None:
    with container_context(Container):
        pass

    print(Container.get_providers())


if __name__ == "__main__":
    main()
