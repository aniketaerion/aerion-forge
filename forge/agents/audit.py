"""Production read-only repository audit agent."""

import json
from datetime import UTC, datetime
from pathlib import Path
from typing import Any

from forge.agents.base import BaseAgent
from forge.core import timed_operation
from forge.models.audit import AuditResult
from forge.planner import AuditPlanner
from forge.reports import AuditReportRenderer
from forge.utils.repository import RepositoryScanner


class RepositoryAuditAgent(BaseAgent):
    """Inspect an arbitrary repository and generate durable engineering reports."""

    def __init__(
        self,
        *args: Any,
        planner: AuditPlanner | None = None,
        renderer: AuditReportRenderer | None = None,
        **kwargs: Any,
    ) -> None:
        super().__init__(*args, **kwargs)
        self.planner = planner or AuditPlanner()
        self.renderer = renderer or AuditReportRenderer()

    def plan(self, **kwargs: Any) -> list[str]:
        """Return the deterministic read-only audit plan."""
        return self.planner.build()

    def execute(self, repository_path: Path | None = None, **kwargs: Any) -> AuditResult:
        """Audit a repository, persist memory, and write all reports."""
        root = (repository_path or self.settings.repository_path).expanduser().resolve()
        started_at = datetime.now(UTC)
        self.logger.info("Audit plan contains %d stages", len(self.plan()))
        try:
            with timed_operation(self.logger, "repository audit", repository=str(root)):
                inventory, dependency_graph, findings = RepositoryScanner(root).scan()
                completed_at = datetime.now(UTC)
                result = AuditResult(
                    repository=str(root),
                    started_at=started_at,
                    completed_at=completed_at,
                    inventory=inventory,
                    dependency_graph=dependency_graph,
                    findings=findings,
                )
                reports = self.renderer.render(result)
                result.reports = {
                    filename: self.write_report(filename, content)
                    for filename, content in reports.items()
                }
                graph_path = self.settings.reports_path / "DEPENDENCY_GRAPH.json"
                graph_path.write_text(
                    json.dumps(dependency_graph.model_dump(), indent=2, ensure_ascii=False) + "\n",
                    encoding="utf-8",
                )
                result.reports[graph_path.name] = graph_path
                self._remember(result)
                self.logger.info("Generated %d reports", len(result.reports))
                return result
        except Exception as exc:
            self.memory.record_execution(
                "repository_audit", "failed", {"repository": str(root), "error": str(exc)}
            )
            raise

    def _remember(self, result: AuditResult) -> None:
        """Persist architecture, dependency, issue, metadata, and run history."""
        inventory = result.inventory
        self.memory.set(
            "architecture_map",
            {
                "repository": result.repository,
                "backend": inventory.backend_files,
                "frontend": inventory.frontend_files,
                "database_migrations": inventory.migrations,
                "apis": inventory.api_files,
                "routes": inventory.route_files,
            },
        )
        self.memory.set("dependency_graph", result.dependency_graph.model_dump())
        self.memory.set(
            "known_issues",
            [finding.model_dump() for finding in result.findings if finding.severity != "info"],
        )
        self.memory.set(
            "project_metadata",
            {
                "repository": result.repository,
                "technologies": inventory.technologies,
                "languages": inventory.languages,
                "file_count": len(inventory.files),
                "last_audited_at": result.completed_at.isoformat(),
            },
        )
        self.memory.append(
            "completed_tasks",
            {
                "task": "repository_audit",
                "completed_at": result.completed_at.isoformat(),
                "repository": result.repository,
            },
        )
        self.memory.record_execution(
            "repository_audit",
            "completed",
            {
                "repository": result.repository,
                "files": len(inventory.files),
                "findings": len(result.findings),
            },
        )
