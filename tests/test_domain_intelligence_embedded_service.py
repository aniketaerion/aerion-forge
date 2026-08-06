from pathlib import Path

from forge.domain_intelligence.embedded.models import (
    EmbeddedAnalysisRequest,
    EmbeddedPlatformKind,
)
from forge.domain_intelligence.embedded.service import (
    EmbeddedIntelligenceService,
)


def initialize_repository(tmp_path: Path) -> None:
    (tmp_path / ".git").mkdir()


def test_embedded_service_analyzes_px4_project(
    tmp_path: Path,
) -> None:
    initialize_repository(tmp_path)
    module = tmp_path / "src" / "modules" / "navigator"
    module.mkdir(parents=True)
    (tmp_path / "CMakeLists.txt").write_text(
        "project(px4)",
        encoding="utf-8",
    )
    (tmp_path / "vehicle.msg").write_text(
        "float32 latitude\n",
        encoding="utf-8",
    )
    (module / "navigator.cpp").write_text(
        "UART_Init();\n",
        encoding="utf-8",
    )

    report = EmbeddedIntelligenceService().analyze(
        EmbeddedAnalysisRequest(
            repository_root=str(tmp_path),
        )
    )

    assert report.project.platforms == (
        EmbeddedPlatformKind.PX4,
    )
    assert report.components[0].name == "navigator"
    assert report.project.build_files == ("CMakeLists.txt",)
    assert len(report.interfaces) >= 1
    assert len(report.messages) == 1


def test_embedded_service_reports_unknown_project(
    tmp_path: Path,
) -> None:
    initialize_repository(tmp_path)

    report = EmbeddedIntelligenceService().analyze(
        EmbeddedAnalysisRequest(
            repository_root=str(tmp_path),
        )
    )

    assert report.project.platforms == (
        EmbeddedPlatformKind.UNKNOWN,
    )
    assert any(
        finding.category == "platform"
        for finding in report.findings
    )