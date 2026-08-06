import json
from pathlib import Path

from forge.domain_intelligence.embedded.models import (
    EmbeddedAnalysisReport,
    EmbeddedComponent,
    EmbeddedComponentKind,
    EmbeddedFinding,
    EmbeddedFindingSeverity,
    EmbeddedInterface,
    EmbeddedInterfaceKind,
    EmbeddedMessage,
    EmbeddedPlatformKind,
    EmbeddedProject,
)
from forge.domain_intelligence.embedded.reporting import (
    embedded_report_markdown,
    embedded_report_summary,
    write_embedded_report_bundle,
)


def example_report() -> EmbeddedAnalysisReport:
    project = EmbeddedProject(
        project_id="embedded-project-1",
        root="firmware",
        platforms=(EmbeddedPlatformKind.PX4,),
        build_files=("CMakeLists.txt",),
    )
    component = EmbeddedComponent(
        component_id="embedded-component-1",
        name="navigator",
        kind=EmbeddedComponentKind.AUTOPILOT_MODULE,
        platform=EmbeddedPlatformKind.PX4,
        source_paths=("src/modules/navigator",),
    )
    interface = EmbeddedInterface(
        interface_id="embedded-interface-1",
        name="uart:navigator.cpp",
        kind=EmbeddedInterfaceKind.UART,
        source_path="src/modules/navigator/navigator.cpp",
    )
    message = EmbeddedMessage(
        message_id="embedded-message-1",
        name="VehicleState",
        protocol="ros2",
        fields=("latitude", "longitude"),
        source_path="msg/VehicleState.msg",
    )
    finding = EmbeddedFinding(
        finding_id="embedded-finding-1",
        category="blocking-delay",
        severity=EmbeddedFindingSeverity.MEDIUM,
        message="Blocking delay detected in embedded code.",
        path="src/control.c",
    )

    return EmbeddedAnalysisReport(
        report_id="embedded-report-1",
        project=project,
        components=(component,),
        interfaces=(interface,),
        messages=(message,),
        findings=(finding,),
    )


def test_embedded_report_summary() -> None:
    summary = embedded_report_summary(example_report())

    assert summary["platforms"] == ("px4",)
    assert summary["component_count"] == 1
    assert summary["interface_count"] == 1
    assert summary["message_count"] == 1
    assert summary["finding_count"] == 1
    assert summary["finding_severity_counts"] == {
        "medium": 1,
    }


def test_embedded_report_markdown() -> None:
    markdown = embedded_report_markdown(example_report())

    assert "# Embedded Domain Intelligence Report" in markdown
    assert "navigator" in markdown
    assert "VehicleState" in markdown
    assert "blocking-delay" in markdown


def test_write_embedded_report_bundle(
    tmp_path: Path,
) -> None:
    paths = write_embedded_report_bundle(
        example_report(),
        tmp_path,
    )

    assert set(paths) == {
        "analysis_json",
        "summary_json",
        "analysis_markdown",
    }
    assert all(path.is_file() for path in paths.values())

    analysis = json.loads(
        paths["analysis_json"].read_text(encoding="utf-8")
    )
    summary = json.loads(
        paths["summary_json"].read_text(encoding="utf-8")
    )
    markdown = paths["analysis_markdown"].read_text(
        encoding="utf-8"
    )

    assert analysis["report_id"] == "embedded-report-1"
    assert summary["component_count"] == 1
    assert "Embedded Domain Intelligence Report" in markdown