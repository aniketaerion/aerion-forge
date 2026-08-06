"""M4.6 Embedded Domain Intelligence public API."""

from forge.domain_intelligence.embedded.errors import (
    EmbeddedConfigurationError,
    EmbeddedIntelligenceError,
    EmbeddedParseError,
    EmbeddedPolicyError,
)
from forge.domain_intelligence.embedded.identifiers import (
    embedded_component_identifier,
    embedded_finding_identifier,
    embedded_interface_identifier,
    embedded_message_identifier,
    embedded_project_identifier,
    embedded_report_identifier,
)
from forge.domain_intelligence.embedded.models import (
    EmbeddedAnalysisReport,
    EmbeddedAnalysisRequest,
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
from forge.domain_intelligence.embedded.policies import (
    EmbeddedIntelligencePolicy,
    resolve_embedded_repository_root,
    validate_embedded_request,
)
from forge.domain_intelligence.embedded.reporting import (
    EmbeddedReportSummary,
    embedded_report_markdown,
    embedded_report_summary,
    write_embedded_report_bundle,
)

__all__ = [
    "EmbeddedAnalysisReport",
    "EmbeddedAnalysisRequest",
    "EmbeddedComponent",
    "EmbeddedComponentKind",
    "EmbeddedConfigurationError",
    "EmbeddedFinding",
    "EmbeddedFindingSeverity",
    "EmbeddedIntelligenceError",
    "EmbeddedIntelligencePolicy",
    "EmbeddedInterface",
    "EmbeddedInterfaceKind",
    "EmbeddedMessage",
    "EmbeddedParseError",
    "EmbeddedPlatformKind",
    "EmbeddedPolicyError",
    "EmbeddedProject",
    "EmbeddedReportSummary",
    "embedded_component_identifier",
    "embedded_finding_identifier",
    "embedded_interface_identifier",
    "embedded_message_identifier",
    "embedded_project_identifier",
    "embedded_report_identifier",
    "embedded_report_markdown",
    "embedded_report_summary",
    "resolve_embedded_repository_root",
    "validate_embedded_request",
    "write_embedded_report_bundle",
]