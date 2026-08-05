from pathlib import Path

from forge.domain_intelligence.api.models import (
    ApiAnalysisRequest,
    ApiStyle,
)
from forge.domain_intelligence.api.service import (
    ApiIntelligenceService,
    default_api_registry,
)


def initialize_repository(tmp_path: Path) -> None:
    (tmp_path / ".git").mkdir()


def test_default_api_registry() -> None:
    assert default_api_registry().names() == (
        "discovery",
        "openapi",
        "rest",
    )


def test_service_discovers_rest_and_openapi(
    tmp_path: Path,
) -> None:
    initialize_repository(tmp_path)

    (tmp_path / "openapi.yaml").write_text(
        """
        openapi: 3.0.0
        info:
          title: ERP API
          version: 1.0.0
        paths:
          /orders:
            get:
              responses:
                "200":
                  description: Success
        """,
        encoding="utf-8",
    )
    (tmp_path / "routes.py").write_text(
        """
        @router.post("/orders")
        def create_order():
            return {}
        """,
        encoding="utf-8",
    )

    report = ApiIntelligenceService().analyze(
        ApiAnalysisRequest(
            repository_root=str(tmp_path),
        )
    )

    assert report.project.styles == (
        ApiStyle.OPENAPI,
        ApiStyle.REST,
    )
    assert len(report.contracts) == 2


def test_service_reports_unknown_api(
    tmp_path: Path,
) -> None:
    initialize_repository(tmp_path)

    report = ApiIntelligenceService().analyze(
        ApiAnalysisRequest(
            repository_root=str(tmp_path),
        )
    )

    assert report.project.styles == (
        ApiStyle.UNKNOWN,
    )