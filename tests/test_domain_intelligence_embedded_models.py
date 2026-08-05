import pytest
from pydantic import ValidationError

from forge.domain_intelligence.embedded.models import (
    EmbeddedAnalysisReport,
    EmbeddedComponent,
    EmbeddedComponentKind,
    EmbeddedFinding,
    EmbeddedFindingSeverity,
    EmbeddedPlatformKind,
    EmbeddedProject,
)


def test_embedded_component_supports_dependencies() -> None:
    component = EmbeddedComponent(
        component_id="component-1",
        name="navigator",
        kind=EmbeddedComponentKind.AUTOPILOT_MODULE,
        platform=EmbeddedPlatformKind.PX4,
        dependencies=("uorb", "hrt"),
    )

    assert component.platform is EmbeddedPlatformKind.PX4
    assert component.dependencies == ("uorb", "hrt")


def test_embedded_project_rejects_duplicate_platforms() -> None:
    with pytest.raises(ValidationError):
        EmbeddedProject(
            project_id="project-1",
            root="firmware",
            platforms=(
                EmbeddedPlatformKind.PX4,
                EmbeddedPlatformKind.PX4,
            ),
        )


def test_embedded_report_rejects_duplicate_findings() -> None:
    project = EmbeddedProject(
        project_id="project-1",
        root="firmware",
        platforms=(EmbeddedPlatformKind.PX4,),
    )
    finding = EmbeddedFinding(
        finding_id="finding-1",
        category="safety",
        severity=EmbeddedFindingSeverity.HIGH,
        message="Unsafe actuator path.",
    )

    with pytest.raises(ValidationError):
        EmbeddedAnalysisReport(
            report_id="report-1",
            project=project,
            findings=(finding, finding),
        )