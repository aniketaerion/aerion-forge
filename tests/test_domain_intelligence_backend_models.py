import pytest
from pydantic import ValidationError

from forge.domain_intelligence.backend.models import (
    BackendAnalysisReport,
    BackendFinding,
    BackendFindingSeverity,
    BackendFramework,
    BackendProject,
    BackendRuntime,
)


def test_backend_project_supports_multiple_frameworks() -> None:
    project = BackendProject(
        project_id="backend-project-1",
        root="apps/api",
        runtimes=(BackendRuntime.NODEJS,),
        frameworks=(
            BackendFramework.NODE,
            BackendFramework.EXPRESS,
        ),
    )

    assert BackendFramework.EXPRESS in project.frameworks


def test_backend_report_rejects_duplicate_findings() -> None:
    project = BackendProject(
        project_id="backend-project-1",
        root="apps/api",
    )
    finding = BackendFinding(
        finding_id="backend-finding-1",
        category="framework",
        severity=BackendFindingSeverity.INFO,
        message="Express detected.",
    )

    with pytest.raises(ValidationError):
        BackendAnalysisReport(
            report_id="backend-report-1",
            project=project,
            findings=(finding, finding),
        )