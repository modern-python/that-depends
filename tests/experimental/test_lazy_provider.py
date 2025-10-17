import pytest

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
