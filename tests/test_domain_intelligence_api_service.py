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


def test_default_api_registry_is_complete() -> None:
    assert default_api_registry().names() == (
        "dependencies",
        "discovery",
        "graphql",
        "openapi",
        "rest",
    )


def test_service_runs_complete_api_pipeline(
    tmp_path: Path,
) -> None:
    initialize_repository(tmp_path)

    (tmp_path / "package.json").write_text(
        """
        {
          "dependencies": {
            "express": "^5.0.0",
            "graphql": "^16.0.0"
          }
        }
        """,
        encoding="utf-8",
    )
    (tmp_path / "openapi.yaml").write_text(
        """
        openapi: 3.0.0
        info:
          title: ERP API
          version: 1.0.0
        paths:
          /v1/orders:
            get:
              operationId: listOrders
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
    (tmp_path / "schema.graphql").write_text(
        """
        type Query {
            orders: [String!]!
        }
        """,
        encoding="utf-8",
    )

    report = ApiIntelligenceService().analyze(
        ApiAnalysisRequest(
            repository_root=str(tmp_path),
        )
    )

    assert report.project.styles == (
        ApiStyle.GRAPHQL,
        ApiStyle.OPENAPI,
        ApiStyle.REST,
    )
    assert len(report.contracts) == 3

    categories = {
        finding.category for finding in report.findings
    }

    assert "dependencies" in categories
    assert "graphql" in categories
    assert "missing_authentication" in categories


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
    assert not report.contracts