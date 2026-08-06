from typer.testing import CliRunner

from forge.autonomous_planning.cli import app

runner = CliRunner()


def test_simulation_outputs_json() -> None:
    result = runner.invoke(
        app,
        ["simulate", "--format", "json"],
    )

    assert result.exit_code == 0
    assert '"step_count": 4' in result.stdout
    assert '"valid": true' in result.stdout


def test_policy_outputs_default_policy() -> None:
    result = runner.invoke(app, ["policy"])

    assert result.exit_code == 0
    assert '"maximum_steps": 50' in result.stdout
    assert '"allow_destructive_steps": false' in result.stdout