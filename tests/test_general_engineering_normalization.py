from forge.general_engineering.normalization import (
    normalize_optional_items,
    normalize_repository_path,
    normalize_text,
)


def test_normalize_text_collapses_whitespace() -> None:
    assert normalize_text("  Add   validation\n  and tests. ") == (
        "Add validation and tests."
    )


def test_optional_items_are_deduplicated_case_insensitively() -> None:
    assert normalize_optional_items(
        ("- Preserve behavior", "preserve behavior", "Add tests")
    ) == ("Preserve behavior", "Add tests")


def test_repository_path_normalization_is_stable() -> None:
    assert normalize_repository_path(r".\src\service.py") == "src/service.py"