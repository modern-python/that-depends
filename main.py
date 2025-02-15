from lib.entry import (
    entry_point_with_explicit,
    entry_point_with_resource,
    entry_point_with_wrapper,
    entry_with_multiple_resources_explicit,
    entry_with_multiple_resources_wrapped,
)


def calling_code() -> None:
    entry_point_with_wrapper()
    entry_point_with_explicit()
    entry_point_with_resource()
    entry_with_multiple_resources_wrapped()
    entry_with_multiple_resources_explicit()


if __name__ == "__main__":
    calling_code()
