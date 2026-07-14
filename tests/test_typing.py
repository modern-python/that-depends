import typing

from typing_extensions import assert_type

from that_depends import Provide, providers
from that_depends.experimental.providers import LazyProvider


int_provider = providers.Object(1)
lazy_provider: LazyProvider[str] = LazyProvider("tests.container.DIContainer.simple_factory")


assert_type(Provide[int_provider], int)
assert_type(Provide[lazy_provider], str)
assert_type(Provide["Container.provider"], typing.Any)
