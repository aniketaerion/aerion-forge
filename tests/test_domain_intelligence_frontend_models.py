from forge.domain_intelligence.frontend.models import FrontendAnalysisRequest


def test_frontend_request_has_safe_defaults() -> None:
    request = FrontendAnalysisRequest(repository_root=".")

    assert "node_modules/**" in request.exclude_patterns
    assert request.max_files == 5000