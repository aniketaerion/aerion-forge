"""Phase 4 domain-intelligence public API."""

from forge.domain_intelligence.errors import (
    DomainIntelligenceConfigurationError,
    DomainIntelligenceError,
    DomainIntelligencePolicyError,
    DomainIntelligenceValidationError,
    DomainPluginCompatibilityError,
    DomainPluginNotFoundError,
    FrontendAnalysisError,
)
from forge.domain_intelligence.identifiers import (
    domain_plugin_identifier,
    frontend_finding_identifier,
    frontend_project_identifier,
    frontend_report_identifier,
    stable_identifier,
)
from forge.domain_intelligence.models import (
    DomainKind,
    DomainPluginManifest,
    FrontendAnalysisReport,
    FrontendAnalysisRequest,
    FrontendFinding,
    FrontendFindingSeverity,
    FrontendFramework,
    FrontendProject,
)
from forge.domain_intelligence.policies import (
    DomainIntelligencePolicy,
    resolve_repository_root,
    validate_frontend_request,
)

__all__ = [
    "DomainIntelligenceConfigurationError",
    "DomainIntelligenceError",
    "DomainIntelligencePolicy",
    "DomainIntelligencePolicyError",
    "DomainIntelligenceValidationError",
    "DomainKind",
    "DomainPluginCompatibilityError",
    "DomainPluginManifest",
    "DomainPluginNotFoundError",
    "FrontendAnalysisError",
    "FrontendAnalysisReport",
    "FrontendAnalysisRequest",
    "FrontendFinding",
    "FrontendFindingSeverity",
    "FrontendFramework",
    "FrontendProject",
    "domain_plugin_identifier",
    "frontend_finding_identifier",
    "frontend_project_identifier",
    "frontend_report_identifier",
    "resolve_repository_root",
    "stable_identifier",
    "validate_frontend_request",
]