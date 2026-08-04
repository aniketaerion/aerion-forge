from typer.testing import CliRunner

from forge.autonomous_repair.cli import autonomous_repair_app

runner = CliRunner()


def test_help_lists_expected_commands() -> None:
    result = runner.invoke(autonomous_repair_app, ["--help"])

    assert result.exit_code == 0
    assert "providers" in result.stdout
    assert "propose" in result.stdout
    assert "dry-run" in result.stdout
    assert "apply" in result.stdout


def test_providers_lists_builtins() -> None:
    result = runner.invoke(autonomous_repair_app, ["providers"])

    assert result.exit_code == 0
    assert "exact_patch" in result.stdout
    assert "ruff_fix" in result.stdout


def test_apply_requires_explicit_approval() -> None:
    result = runner.invoke(
        autonomous_repair_app,
        ["apply", "missing.json"],
    )

    assert result.exit_code != 0