from typer.testing import CliRunner

from forge.autonomous_orchestration.cli import app

runner = CliRunner()


def test_status_sample_command() -> None:
    result = runner.invoke(app, ["status-sample"])

    assert result.exit_code == 0
    normalized = " ".join(result.stdout.split())
    assert "Autonomous Mission Orchestration" in normalized
    assert "paused" in normalized


def test_report_sample_command() -> None:
    result = runner.invoke(app, ["report-sample"])

    assert result.exit_code == 0
    assert '"state": "paused"' in result.stdout