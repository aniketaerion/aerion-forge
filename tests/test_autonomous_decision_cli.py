from typer.testing import CliRunner

from forge.autonomous_decision.cli import app

runner = CliRunner()


def test_simulate_command() -> None:
    result = runner.invoke(app, ["simulate"])

    assert result.exit_code == 0
    normalized = " ".join(result.stdout.split())
    assert "Autonomous Decision Simulation" in normalized
    assert "select_action" in normalized


def test_simulate_without_evidence_stops() -> None:
    result = runner.invoke(
        app,
        ["simulate", "--no-evidence"],
    )

    assert result.exit_code == 0
    assert "no_safe_action" in result.stdout


def test_report_sample_command() -> None:
    result = runner.invoke(app, ["report-sample"])

    assert result.exit_code == 0
    assert '"disposition": "select_action"' in result.stdout