from pathlib import Path

import pytest

from forge.domain_intelligence.errors import DomainIntelligencePolicyError
from forge.domain_intelligence.models import FrontendAnalysisRequest
from forge.domain_intelligence.policies import (
    DomainIntelligencePolicy,
    resolve_repository_root,
    validate_frontend_request,
)


def test_repository_root_requires_git(tmp_path: Path) -> None:
    with pytest.raises(DomainIntelligencePolicyError):
        resolve_repository_root(tmp_path, DomainIntelligencePolicy())


def test_request_rejects_repository_escape() -> None:
    request = FrontendAnalysisRequest(
        repository_root=".",
        project_root="../outside",
    )

    with pytest.raises(DomainIntelligencePolicyError):
        validate_frontend_request(request, DomainIntelligencePolicy())


def test_request_respects_file_limit() -> None:
    request = FrontendAnalysisRequest(repository_root=".", max_files=100)

    with pytest.raises(DomainIntelligencePolicyError):
        validate_frontend_request(
            request,
            DomainIntelligencePolicy(max_files=10),
        )