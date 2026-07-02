from unittest.mock import Mock

import pytest

from that_depends import providers
from that_depends.experimental import LazyProvider


def test_lazy_provider_incorrect_initialization() -> None:
    with pytest.raises(
        ValueError,
        match=r"You must provide either import_string "
        "OR both module_string AND provider_string, but not both or neither.",
    ):
        LazyProvider(module_string="3213")  # type: ignore[call-overload]

    with pytest.raises(ValueError, match=r"Invalid import_string ''"):
        LazyProvider("")

    with pytest.raises(ValueError, match=r"Invalid provider_string ''"):
        LazyProvider(module_string="some.module", provider_string="")

    with pytest.raises(ValueError, match=r"Invalid module_string '.'"):
        LazyProvider(module_string=".", provider_string="SomeProvider")

    with pytest.raises(ValueError, match=r"Invalid import_string 'import.'"):
        LazyProvider("import.")


def test_lazy_provider_incorrect_import_string() -> None:
    p = LazyProvider("some.random.path")
    with pytest.raises(ImportError):
        p.resolve_sync()


def test_lazy_provider_resolves_module_and_provider_strings() -> None:
    p = LazyProvider(module_string="tests.experimental.test_container_2", provider_string="Container2.obj_2")

    assert p.resolve_sync() == 2  # noqa: PLR2004


def test_collection_registration_does_not_resolve_lazy_provider(monkeypatch: pytest.MonkeyPatch) -> None:
    import_module_mock = Mock()
    monkeypatch.setattr("that_depends.experimental.providers.importlib.import_module", import_module_mock)

    lazy_provider = LazyProvider(module_string="some.module", provider_string="Container.provider")

    providers.Dict(dep=lazy_provider)
    providers.List(lazy_provider)

    import_module_mock.assert_not_called()
