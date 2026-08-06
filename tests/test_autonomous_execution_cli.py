from typer.testing import CliRunner

from forge.autonomous_execution.cli import app

runner = CliRunner()


def test_create_dry_run_command() -> None:
    result = runner.invoke(
        app,
        [
            "create-dry-run",
            "--mission-id",
            "mission-1",
            "--plan-id",
            "plan-1",
            "--step-id",
            "step-1",
        ],
    )

    assert result.exit_code == 0
    normalized = " ".join(result.stdout.split())
    assert "Autonomous Execution Dry Run" in normalized
    assert "True" in normalized


def test_report_sample_command() -> None:
    result = runner.invoke(
        app,
        ["report-sample"],
    )

    assert result.exit_code == 0
    assert '"state": "succeeded"' in result.stdout