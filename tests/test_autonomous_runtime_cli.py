from typer.testing import CliRunner

from forge.autonomous_runtime.cli import app

runner = CliRunner()


def test_create_dry_run_command() -> None:
    result = runner.invoke(
        app,
        [
            "create-dry-run",
            "--objective",
            "Inspect mission contracts.",
            "--repository-root",
            ".",
        ],
    )

    assert result.exit_code == 0
    normalized = " ".join(result.stdout.split())
    assert "Autonomous Mission Dry Run" in normalized
    assert "received" in normalized


def test_simulate_transition_command() -> None:
    result = runner.invoke(
        app,
        [
            "simulate-transition",
            "--target",
            "qualifying",
        ],
    )

    assert result.exit_code == 0
    assert '"state": "qualifying"' in result.stdout