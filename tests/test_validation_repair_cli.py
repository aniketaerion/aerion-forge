from typer.testing import CliRunner

from forge.validation_repair.cli import repair_app

runner = CliRunner()


def test_repair_help_lists_commands() -> None:
    result = runner.invoke(repair_app, ["--help"])
    assert result.exit_code == 0
    assert "validate" in result.stdout
    assert "plan" in result.stdout