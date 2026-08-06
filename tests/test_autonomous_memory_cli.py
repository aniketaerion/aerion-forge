from typer.testing import CliRunner

from forge.autonomous_memory.cli import app

runner = CliRunner()


def test_memory_simulation_outputs_json() -> None:
    result = runner.invoke(
        app,
        ["simulate", "--format", "json"],
    )

    assert result.exit_code == 0
    assert '"record_count": 1' in result.stdout


def test_memory_policy_command_outputs_policy() -> None:
    result = runner.invoke(app, ["policy"])

    assert result.exit_code == 0
    assert '"reject_secrets": true' in result.stdout