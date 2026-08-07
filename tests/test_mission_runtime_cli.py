from typer.testing import CliRunner

from forge.mission_runtime.cli import app

runner = CliRunner()


def test_mission_runtime_about_command() -> None:
    result = runner.invoke(app, ["about"])

    assert result.exit_code == 0
    assert "M5.8 Forge Mission Runtime" in result.stdout