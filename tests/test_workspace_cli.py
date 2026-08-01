from pathlib import Path

from typer.testing import CliRunner

from forge.cli import app

runner = CliRunner()


def environment(tmp_path: Path) -> dict[str, str]:
    return {
        "AERION_MEMORY_PATH": str(tmp_path / "memory"),
        "AERION_LOGS_PATH": str(tmp_path / "logs"),
        "AERION_REPORTS_PATH": str(tmp_path / "reports"),
        "AERION_WORKSPACE_PATH": str(tmp_path / "definitions"),
    }


def test_workspace_cli_lifecycle_persists_between_invocations(tmp_path: Path) -> None:
    repository = tmp_path / "repo"
    repository.mkdir()
    (repository / ".git").mkdir()
    env = environment(tmp_path)

    added = runner.invoke(
        app, ["workspace", "add", "ERP", str(repository), "--type", "ERP"], env=env
    )
    listed = runner.invoke(app, ["workspace", "list"], env=env)
    selected = runner.invoke(app, ["workspace", "use", "ERP"], env=env)
    current = runner.invoke(app, ["workspace", "current"], env=env)
    renamed = runner.invoke(app, ["workspace", "rename", "ERP", "Core"], env=env)
    validated = runner.invoke(app, ["workspace", "validate", "Core"], env=env)
    removed = runner.invoke(app, ["workspace", "remove", "Core"], env=env)

    assert added.exit_code == 0
    assert listed.exit_code == 0 and "ERP" in listed.stdout
    assert selected.exit_code == 0
    assert current.exit_code == 0 and '"name": "ERP"' in current.stdout
    assert renamed.exit_code == 0
    assert validated.exit_code == 0 and "healthy" in validated.stdout
    assert removed.exit_code == 0
    assert (tmp_path / "memory" / "workspaces.json").is_file()
    assert (tmp_path / "logs" / "forge.log").is_file()


def test_workspace_cli_handles_invalid_path_without_traceback(tmp_path: Path) -> None:
    result = runner.invoke(
        app,
        ["workspace", "add", "Missing", str(tmp_path / "missing")],
        env=environment(tmp_path),
    )

    assert result.exit_code == 1
    assert "Workspace error" in result.stdout
    assert "does not exist" in result.stdout
