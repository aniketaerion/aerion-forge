import json
from pathlib import Path

from forge.domain_intelligence.frontend.service import (
    FrontendIntelligenceService,
)
from forge.domain_intelligence.models import (
    FrontendAnalysisRequest,
    FrontendFramework,
)


def initialize_repository(tmp_path: Path) -> None:
    (tmp_path / ".git").mkdir()


def test_service_discovers_react_vite_project(
    tmp_path: Path,
) -> None:
    initialize_repository(tmp_path)
    (tmp_path / "src").mkdir()
    (tmp_path / "package-lock.json").write_text(
        "{}",
        encoding="utf-8",
    )
    (tmp_path / "package.json").write_text(
        json.dumps(
            {
                "dependencies": {"react": "^19.0.0"},
                "devDependencies": {"vite": "^7.0.0"},
            }
        ),
        encoding="utf-8",
    )

    report = FrontendIntelligenceService().analyze(
        FrontendAnalysisRequest(
            repository_root=str(tmp_path),
        )
    )

    assert report.project.frameworks == (
        FrontendFramework.REACT,
        FrontendFramework.VITE,
    )
    assert report.project.package_manager == "npm"
    assert len(report.findings) == 2


def test_service_reports_unknown_project(
    tmp_path: Path,
) -> None:
    initialize_repository(tmp_path)

    report = FrontendIntelligenceService().analyze(
        FrontendAnalysisRequest(
            repository_root=str(tmp_path),
        )
    )

    assert report.project.frameworks == (
        FrontendFramework.UNKNOWN,
    )
    assert not report.findings