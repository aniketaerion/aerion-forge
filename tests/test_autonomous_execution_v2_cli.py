from typer.testing import CliRunner

from forge.autonomous_execution_v2.cli import app

runner = CliRunner()


def test_simulate_outputs_json() -> None:
    result = runner.invoke(
        app,
        ["simulate", "--format", "json"],
    )

    assert result.exit_code == 0
    assert '"state": "succeeded"' in result.stdout
    assert '"step_count": 1' in result.stdout


def test_status_outputs_run_state() -> None:
    result = runner.invoke(app, ["status"])

    assert result.exit_code == 0
    assert '"completed_steps": 1' in result.stdout
    assert '"state": "succeeded"' in result.stdout


def test_policy_outputs_safe_defaults() -> None:
    result = runner.invoke(app, ["policy"])

    assert result.exit_code == 0
    assert '"allow_destructive_execution": false' in result.stdout
    assert '"maximum_attempts_per_step": 3' in result.stdout