from pathlib import Path

import pytest
from typer.testing import CliRunner

from forge.cli import app

runner = CliRunner()


def environment(tmp_path: Path) -> dict[str, str]:
    return {
        "AERION_MEMORY_PATH": str(tmp_path / "memory"),
        "AERION_LOGS_PATH": str(tmp_path / "logs"),
        "AERION_REPORTS_PATH": str(tmp_path / "reports"),
        "AERION_WORKSPACE_PATH": str(tmp_path / "definitions"),
        "AERION_GRAPH_MAX_NODES": "10000",
        "AERION_GRAPH_MAX_EDGES": "30000",
    }


def repository(path: Path) -> Path:
    path.mkdir()
    (path / ".git").mkdir()
    (path / "package.json").write_text('{"dependencies":{"react":"19"}}', encoding="utf-8")
    (path / "App.tsx").write_text("content", encoding="utf-8")
    return path


def test_graph_workspace_modes_validation_and_reports(tmp_path: Path) -> None:
    root = repository(tmp_path / "repo")
    env = environment(tmp_path)
    assert runner.invoke(app, ["workspace", "add", "ERP", str(root)], env=env).exit_code == 0
    assert runner.invoke(app, ["workspace", "use", "ERP"], env=env).exit_code == 0
    assert runner.invoke(app, ["inspect", "ERP"], env=env).exit_code == 0
    assert runner.invoke(app, ["index", "ERP"], env=env).exit_code == 0

    summary = runner.invoke(app, ["graph", "--summary"], env=env)
    json_result = runner.invoke(app, ["graph", "ERP", "--json"], env=env)
    changes = runner.invoke(app, ["graph", "ERP", "--changes"], env=env)
    orphans = runner.invoke(app, ["graph", "ERP", "--orphans"], env=env)
    verbose = runner.invoke(app, ["graph", "ERP", "--verbose"], env=env)
    validation = runner.invoke(app, ["graph", "ERP", "--validate"], env=env)

    assert summary.exit_code == 0 and "Graph state:" in summary.stdout
    assert json_result.exit_code == 0 and '"graph"' in json_result.stdout
    assert changes.exit_code == 0 and '"unchanged_nodes"' in changes.stdout
    assert orphans.exit_code == 0 and '"unassigned_file_ids"' in orphans.stdout
    assert verbose.exit_code == 0 and "Source index:" in verbose.stdout
    assert validation.exit_code == 0 and '"valid": true' in validation.stdout
    assert len(list((tmp_path / "reports").glob("KNOWLEDGE_*"))) == 9


def test_graph_direct_path_and_input_exit_codes(tmp_path: Path) -> None:
    root = repository(tmp_path / "repo")
    env = environment(tmp_path)
    invalid = runner.invoke(app, ["graph", "missing"], env=env)
    missing_index = runner.invoke(app, ["graph", str(root)], env=env)
    runner.invoke(app, ["index", str(root)], env=env)
    missing_discovery = runner.invoke(app, ["graph", str(root)], env=env)
    runner.invoke(app, ["inspect", str(root)], env=env)
    successful = runner.invoke(app, ["graph", str(root)], env=env)

    assert invalid.exit_code == 2
    assert missing_index.exit_code == 4
    assert missing_discovery.exit_code == 3
    assert successful.exit_code == 0


def test_graph_current_directory_fallback(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    root = repository(tmp_path / "repo")
    env = environment(tmp_path)
    runner.invoke(app, ["inspect", str(root)], env=env)
    runner.invoke(app, ["index", str(root)], env=env)
    monkeypatch.chdir(root)

    result = runner.invoke(app, ["graph", "--summary"], env=env)

    assert result.exit_code == 0
