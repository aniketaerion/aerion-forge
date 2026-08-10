from pathlib import Path

from forge.general_engineering.validation_commands import resolve_validation_commands


def test_python_capabilities_resolve_without_shell(tmp_path: Path) -> None:
    (tmp_path / "pyproject.toml").write_text("[project]\nname='demo'\n", encoding="utf-8")
    commands = resolve_validation_commands(
        tmp_path,
        ("repository_tests", "static_analysis", "focused_tests"),
    )
    rendered = tuple(item.argv[2:] for item in commands)
    assert ("pytest", "-p", "no:cacheprovider") in rendered
    assert ("ruff", "check", ".") in rendered
    assert ("mypy", ".") in rendered
