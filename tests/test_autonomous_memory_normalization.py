from forge.autonomous_memory.normalization import (
    normalize_scope,
    normalize_statement,
    normalize_tags,
)


def test_statement_normalization() -> None:
    assert (
        normalize_statement("  Repository   Uses Python! ")
        == "repository uses python"
    )


def test_tags_are_normalized() -> None:
    assert normalize_tags(
        ("Architecture", "architecture", "Safe Change")
    ) == ("architecture", "safe-change")


def test_scope_uses_forward_slashes() -> None:
    assert normalize_scope(
        ("forge\\planning", "forge/planning")
    ) == ("forge/planning",)