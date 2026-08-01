import logging
from pathlib import Path

from forge.agents import RepositoryAuditAgent
from forge.config import Settings
from forge.memory import JsonMemoryStore


def test_audit_scans_repository_and_writes_reports(tmp_path: Path) -> None:
    repository = tmp_path / "project"
    repository.mkdir()
    (repository / "app.py").write_text("# TODO add tests\n", encoding="utf-8")
    (repository / "requirements.txt").write_text("pydantic>=2\n", encoding="utf-8")
    output = tmp_path / "reports"
    settings = Settings(
        repository_path=repository,
        reports_path=output,
        memory_path=tmp_path / "memory",
        logs_path=tmp_path / "logs",
        workspace_path=tmp_path / "workspace",
        _env_file=None,  # type: ignore[call-arg]
    )
    settings.ensure_runtime_directories()
    agent = RepositoryAuditAgent(
        settings=settings,
        logger=logging.getLogger("test-audit"),
        memory=JsonMemoryStore(settings.memory_path / "knowledge.json"),
        tools={},
    )
    result = agent.execute(repository)
    assert len(result.inventory.files) == 2
    assert result.dependency_graph.nodes[0].name == "pydantic"
    assert (output / "PROJECT_ARCHITECTURE.md").is_file()
    assert (output / "DEPENDENCY_GRAPH.json").is_file()
    assert any(finding.category == "TODO" for finding in result.findings)
