"""Runtime, target, determinism, persistence, reports, and query tests."""

import hashlib
import json
from pathlib import Path

import pytest
from typer.testing import CliRunner

from forge.cli import app
from forge.diagnostics.errors import (
    DiagnosticSchemaMismatchError,
    DiagnosticStoreCorruptionError,
)
from forge.diagnostics.models import DiagnosticConfiguration, HealthStatus
from forge.diagnostics.query import DiagnosticQuery
from forge.diagnostics.service import DiagnosticService
from forge.diagnostics.store import DiagnosticRepository


def service(tmp_path: Path, *, probe: bool = True) -> DiagnosticService:
    root = tmp_path / "forge-root"
    (root / "forge").mkdir(parents=True)
    (root / "pyproject.toml").write_text(
        '[project]\nname="fixture"\nversion="0"\nrequires-python=">=3.11"\n', encoding="utf-8"
    )
    memory = tmp_path / "memory"
    reports = tmp_path / "reports"
    memory.mkdir()
    reports.mkdir()
    return DiagnosticService(
        root,
        memory,
        reports,
        DiagnosticConfiguration(write_probe_enabled=probe),
    )


def test_runtime_is_deterministic_persisted_and_reported(tmp_path: Path) -> None:
    diagnostics = service(tmp_path)
    first = diagnostics.health()
    first_bytes = (diagnostics.reports_path / "RUNTIME_HEALTH.json").read_bytes()
    second = diagnostics.health()
    assert first.snapshot.diagnostic_fingerprint == second.snapshot.diagnostic_fingerprint
    assert first.snapshot.generation.generation_id == second.snapshot.generation.generation_id
    assert first_bytes == (diagnostics.reports_path / "RUNTIME_HEALTH.json").read_bytes()
    assert (diagnostics.memory_path / "diagnostics.json").is_file()
    assert not list(diagnostics.memory_path.glob("*.tmp"))
    assert not list(diagnostics.reports_path.glob("*.tmp"))
    assert not list(diagnostics.memory_path.glob("*write-probe*"))


def test_disabled_probe_is_unknown_and_not_healthy(tmp_path: Path) -> None:
    diagnostics = service(tmp_path, probe=False)
    result = diagnostics.health(persist=False, reports=False)
    query = DiagnosticQuery(result.snapshot)
    assert query.get_result("persistence-memory-directory").status is HealthStatus.UNKNOWN
    assert not query.is_runtime_healthy()


def test_target_missing_states_are_actionable_without_repository_scan(tmp_path: Path) -> None:
    diagnostics = service(tmp_path)
    target = tmp_path / "target"
    target.mkdir()
    result = diagnostics.diagnose(str(target), persist=False, reports=False)
    query = DiagnosticQuery(result.snapshot)
    discovery = query.get_result("discovery-state-present")
    index = query.get_result("index-state-present")
    graph = query.get_result("knowledge-graph-state-present")
    assert discovery.status is HealthStatus.DEGRADED
    assert index.status is HealthStatus.DEGRADED
    assert graph.status is HealthStatus.DEGRADED
    assert discovery.corrective_actions[0].command == "forge inspect <target>"
    assert index.corrective_actions[0].command == "forge index <target>"
    assert graph.corrective_actions[0].command == "forge graph <target>"
    assert list(target.iterdir()) == []


def test_query_api_is_typed_sorted_and_non_mutating(tmp_path: Path) -> None:
    result = service(tmp_path).health(persist=False, reports=False)
    query = DiagnosticQuery(result.snapshot)
    assert [item.check_id for item in query.list_results()] == sorted(
        item.check_id for item in result.snapshot.results
    )
    assert query.get_summary() == result.snapshot.summary
    assert query.get_statistics() == result.snapshot.statistics
    assert query.get_generation() == result.snapshot.generation
    assert query.get_diagnostic_fingerprint() == result.snapshot.diagnostic_fingerprint
    assert isinstance(query.list_blocking_results(), tuple)
    assert isinstance(query.list_actionable_results(), tuple)


@pytest.mark.parametrize(
    ("content", "error"),
    [
        ("not-json", DiagnosticStoreCorruptionError),
        ('{"schema_version":"9.0"}', DiagnosticSchemaMismatchError),
    ],
)
def test_diagnostic_store_corruption_and_schema_are_explicit(
    tmp_path: Path, content: str, error: type[Exception]
) -> None:
    path = tmp_path / "diagnostics.json"
    path.write_text(content, encoding="utf-8")
    with pytest.raises(error):
        DiagnosticRepository(path).load()


def test_reports_are_portable_and_contain_no_probe_names(tmp_path: Path) -> None:
    diagnostics = service(tmp_path)
    target = tmp_path / "private" / "repository"
    target.mkdir(parents=True)
    result = diagnostics.diagnose(str(target))
    reports = b"".join(path.read_bytes() for path in diagnostics.reports_path.iterdir())
    persisted = (diagnostics.memory_path / "diagnostics.json").read_bytes()
    assert str(target).encode() not in reports + persisted
    assert b"write-probe" not in reports + persisted
    digest = hashlib.sha256(
        (diagnostics.reports_path / "DIAGNOSTIC_RESULTS.json").read_bytes()
    ).hexdigest()
    assert len(digest) == 64
    summary = json.loads(
        (diagnostics.reports_path / "DIAGNOSTIC_SUMMARY.json").read_text()
    )
    assert summary["total_checks"] == len(result.snapshot.results)


def test_diagnostic_cli_commands_and_invalid_filter(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    memory = tmp_path / "memory"
    reports = tmp_path / "reports"
    target = tmp_path / "target"
    target.mkdir()
    monkeypatch.setenv("FORGE_PERSISTENCE_MEMORY_DIRECTORY", str(memory))
    monkeypatch.setenv("FORGE_REPORTING_OUTPUT_DIRECTORY", str(reports))
    runner = CliRunner()
    health = runner.invoke(app, ["health", "--check", "runtime-python-version", "--json"])
    assert health.exit_code == 0
    assert '"overall_status": "healthy"' in health.stdout
    diagnose = runner.invoke(
        app, ["diagnose", str(target), "--check", "target-resolvable", "--summary"]
    )
    assert diagnose.exit_code == 0
    assert "Overall Status: HEALTHY" in diagnose.stdout
    invalid = runner.invoke(app, ["health", "--category", "not-real"])
    assert invalid.exit_code == 2
    assert "Diagnostic input error" in invalid.stdout
