import json
from pathlib import Path

from forge.domain_intelligence.frontend.service import (
    FrontendIntelligenceService,
    default_frontend_registry,
)
from forge.domain_intelligence.models import (
    FrontendAnalysisRequest,
    FrontendFramework,
)


def initialize_repository(tmp_path: Path) -> None:
    (tmp_path / ".git").mkdir()


def test_default_registry_contains_all_m41_analyzers() -> None:
    assert default_frontend_registry().names() == (
        "components",
        "hooks",
        "nextjs",
        "react",
        "routing",
        "state-management",
        "styling",
        "vite",
    )


def test_service_runs_complete_frontend_pipeline(
    tmp_path: Path,
) -> None:
    initialize_repository(tmp_path)
    source = tmp_path / "src"
    source.mkdir()

    (tmp_path / "package-lock.json").write_text(
        "{}",
        encoding="utf-8",
    )
    (tmp_path / "package.json").write_text(
        json.dumps(
            {
                "dependencies": {
                    "react": "^19.0.0",
                    "zustand": "^5.0.0",
                },
                "devDependencies": {
                    "vite": "^7.0.0",
                    "tailwindcss": "^4.0.0",
                },
            }
        ),
        encoding="utf-8",
    )
    (source / "App.tsx").write_text(
        """
        export function App() {
            const mission = useMission()
            return <Route path="/missions" element={<div />} />
        }
        """,
        encoding="utf-8",
    )
    (source / "app.css").write_text(
        ".root {}",
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
    assert report.project.component_files == ("src/App.tsx",)
    assert report.project.route_files == ("src/App.tsx",)

    categories = {
        finding.category
        for finding in report.findings
    }
    assert {
        "build_tool",
        "component",
        "framework",
        "hooks",
        "routing",
        "state_management",
        "styling",
    }.issubset(categories)


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