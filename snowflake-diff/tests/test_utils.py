from scripts.utils import safe_name


def test_safe_name_replaces_and_trims() -> None:
    assert safe_name("FACT SALES$2025") == "FACT_SALES_2025"


def test_safe_name_empty_returns_unnamed() -> None:
    assert safe_name("") == "unnamed"
