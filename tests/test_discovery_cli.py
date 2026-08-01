import json
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


def test_inspect_workspace_generates_reports_and_persists_result(tmp_path: Path) -> None:
    repository = tmp_path / "repo"
    repository.mkdir()
    (repository / ".git").mkdir()
    (repository / "requirements.txt").write_text("pytest>=8\n", encoding="utf-8")
    env = environment(tmp_path)
    assert runner.invoke(app, ["workspace", "add", "ERP", str(repository)], env=env).exit_code == 0

    result = runner.invoke(app, ["inspect", "ERP", "--verbose"], env=env)

    assert result.exit_code == 0
    assert "Repository:" in result.stdout
    expected = {
        "PROJECT.json",
        "TECH_STACK.json",
        "APPLICATIONS.json",
        "DEPENDENCIES.json",
        "BUILD_SYSTEM.json",
        "TEST_FRAMEWORKS.json",
        "CONFIGURATION.json",
        "DIRECTORY_STRUCTURE.json",
        "PROJECT_SUMMARY.md",
        "TECHNOLOGY_SUMMARY.md",
        "APPLICATION_SUMMARY.md",
    }
    assert expected == {path.name for path in (tmp_path / "reports").iterdir()}
    memory = json.loads((tmp_path / "memory" / "discovery.json").read_text(encoding="utf-8"))
    assert len(memory["results"]) == 1
    assert memory["latest_result_id"] in memory["results"]


def test_inspect_json_and_broken_target_modes(tmp_path: Path) -> None:
    repository = tmp_path / "node"
    repository.mkdir()
    (repository / "package.json").write_text("{}", encoding="utf-8")
    env = environment(tmp_path)

    json_result = runner.invoke(app, ["inspect", str(repository), "--json"], env=env)
    broken = runner.invoke(app, ["inspect", "unknown-workspace"], env=env)

    assert json_result.exit_code == 0
    assert '"repository_name": "node"' in json_result.stdout
    assert broken.exit_code == 1
    assert "Inspection failed" in broken.stdout
