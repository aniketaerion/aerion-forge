"""Business-domain plugin surface for M4.5."""

from __future__ import annotations

from dataclasses import dataclass

from forge.domain_intelligence.business_domain.models import (
    BusinessDomainAnalysisReport,
    BusinessDomainAnalysisRequest,
)
from forge.domain_intelligence.business_domain.service import (
    BusinessDomainIntelligenceService,
)


@dataclass(frozen=True, slots=True)
class BusinessDomainPlugin:
    """Adapter exposing business-domain intelligence as a plugin."""

    name: str = "business-domain"
    version: str = "m4.5"

    def analyze(
        self,
        request: BusinessDomainAnalysisRequest,
    ) -> BusinessDomainAnalysisReport:
        return BusinessDomainIntelligenceService().analyze(request)


def business_domain_plugin() -> BusinessDomainPlugin:
    """Return the default business-domain plugin."""
    return BusinessDomainPlugin()