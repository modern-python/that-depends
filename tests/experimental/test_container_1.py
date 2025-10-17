from tests.experimental.test_container_2 import Container2
from that_depends import BaseContainer, providers
from that_depends.experimental import LazyProvider


class Container1(BaseContainer):
    """Test Container 1."""

    alias = "container_1"
    obj_1 = providers.Object(1)
    obj_2 = LazyProvider(module_string="tests.experimental.test_container_2", provider_string="Container2.obj_2")


def test_lazy_provider_resolution_sync() -> None:
    assert Container2.obj_2.resolve_sync() == 2  # noqa: PLR2004
