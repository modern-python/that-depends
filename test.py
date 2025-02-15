from that_depends import BaseContainer, container_context, providers


class Container(BaseContainer):
    """Container for the application."""

    default_scope = None

    resource = providers.Factory(lambda: 42)


def main() -> None:
    with container_context(Container):
        pass


if __name__ == "__main__":
    main()
