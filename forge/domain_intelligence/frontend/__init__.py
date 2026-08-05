"""M4.1 Frontend and UI Intelligence."""

from forge.domain_intelligence.frontend.errors import FrontendAnalysisError
from forge.domain_intelligence.frontend.identifiers import (
    frontend_finding_identifier,
    frontend_project_identifier,
    frontend_report_identifier,
)
from forge.domain_intelligence.frontend.models import (
    FrontendAnalysisReport,
    FrontendAnalysisRequest,
    FrontendFinding,
    FrontendFindingSeverity,
    FrontendFramework,
    FrontendProject,
)
from forge.domain_intelligence.frontend.policies import (
    DomainIntelligencePolicy,
    resolve_repository_root,
    validate_frontend_request,
)

__all__ = [
    "DomainIntelligencePolicy",
    "FrontendAnalysisError",
    "FrontendAnalysisReport",
    "FrontendAnalysisRequest",
    "FrontendFinding",
    "FrontendFindingSeverity",
    "FrontendFramework",
    "FrontendProject",
    "frontend_finding_identifier",
    "frontend_project_identifier",
    "frontend_report_identifier",
    "resolve_repository_root",
    "validate_frontend_request",
]