import pytest
from pydantic import ValidationError

from forge.domain_intelligence.models import (
    FrontendAnalysisReport,
    FrontendFinding,
    FrontendFindingSeverity,
    FrontendFramework,
    FrontendProject,
)


def test_frontend_project_accepts_multiple_frameworks() -> None:
    project = FrontendProject(
        project_id="project-1",
        root="apps/erp",
        frameworks=(FrontendFramework.REACT, FrontendFramework.VITE),
    )

    assert FrontendFramework.REACT in project.frameworks


def test_report_rejects_duplicate_findings() -> None:
    project = FrontendProject(project_id="project-1", root="apps/erp")
    finding = FrontendFinding(
        finding_id="finding-1",
        category="architecture",
        severity=FrontendFindingSeverity.MEDIUM,
        message="Example",
    )

    with pytest.raises(ValidationError):
        FrontendAnalysisReport(
            report_id="report-1",
            project=project,
            findings=(finding, finding),
        )