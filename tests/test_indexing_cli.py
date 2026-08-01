import json
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
        "AERION_INDEX_MAX_HASH_BYTES": "1048576",
        "AERION_INDEX_HASH_CHUNK_BYTES": "1024",
        "AERION_INDEX_MAX_FILES": "1000",
    }


def make_repository(path: Path) -> Path:
    path.mkdir()
    (path / ".git").mkdir()
    (path / "app.py").write_text("value = 1", encoding="utf-8")
    return path


def test_index_workspace_modes_and_persisted_refresh(tmp_path: Path) -> None:
    repository = make_repository(tmp_path / "repo")
    env = environment(tmp_path)
    assert runner.invoke(app, ["workspace", "add", "ERP", str(repository)], env=env).exit_code == 0
    assert runner.invoke(app, ["workspace", "use", "ERP"], env=env).exit_code == 0

    summary = runner.invoke(app, ["index", "--summary"], env=env)
    json_result = runner.invoke(app, ["index", "ERP", "--json"], env=env)
    changes = runner.invoke(app, ["index", "ERP", "--changes"], env=env)
    verbose = runner.invoke(app, ["index", "ERP", "--verbose"], env=env)

    assert summary.exit_code == 0 and "State:" in summary.stdout
    assert json_result.exit_code == 0 and '"project_index"' in json_result.stdout
    assert changes.exit_code == 0 and '"unchanged"' in changes.stdout
    assert verbose.exit_code == 0 and "Generation:" in verbose.stdout
    persisted = json.loads((tmp_path / "memory" / "index.json").read_text(encoding="utf-8"))
    assert len(persisted["repositories"]) == 1


def test_index_direct_path_and_current_directory_fallback(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    repository = make_repository(tmp_path / "direct")
    env = environment(tmp_path)
    direct = runner.invoke(app, ["index", str(repository)], env=env)
    monkeypatch.chdir(repository)
    current = runner.invoke(app, ["index", "--summary"], env=env)

    assert direct.exit_code == 0
    assert current.exit_code == 0


def test_index_cli_exit_codes(tmp_path: Path) -> None:
    invalid = runner.invoke(app, ["index", "missing"], env=environment(tmp_path))
    repository = make_repository(tmp_path / "limited")
    (repository / "second.py").write_text("value = 2", encoding="utf-8")
    limited_env = environment(tmp_path)
    limited_env["AERION_INDEX_MAX_FILES"] = "1"
    limited = runner.invoke(app, ["index", str(repository)], env=limited_env)

    assert invalid.exit_code == 2
    assert "Index target error" in invalid.stdout
    assert limited.exit_code == 3
    assert "Indexing failed" in limited.stdout


def test_index_cli_reports_corrupt_persistence_with_exit_four(tmp_path: Path) -> None:
    repository = make_repository(tmp_path / "repo")
    memory = tmp_path / "memory"
    memory.mkdir()
    (memory / "index.json").write_text("invalid", encoding="utf-8")

    result = runner.invoke(app, ["index", str(repository)], env=environment(tmp_path))

    assert result.exit_code == 4
    assert "Index persistence error" in result.stdout


def test_index_cli_report_failure_uses_exit_five(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    repository = make_repository(tmp_path / "repo")

    def fail(*args: object, **kwargs: object) -> dict[str, str]:
        from forge.indexing import IndexReportError

        raise IndexReportError("report failure")

    monkeypatch.setattr("forge.indexing.renderer.IndexRenderer.render", fail)
    result = runner.invoke(app, ["index", str(repository)], env=environment(tmp_path))

    assert result.exit_code == 5
    assert "Index report error" in result.stdout
