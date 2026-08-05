"""Deterministic identifiers for M4.5 Business Domain Intelligence."""

from __future__ import annotations

from typing import Any

from forge.domain_intelligence.identifiers import stable_identifier


def business_domain_project_identifier(payload: Any) -> str:
    return stable_identifier("business-domain-project", payload)


def business_entity_identifier(payload: Any) -> str:
    return stable_identifier("business-entity", payload)


def business_workflow_identifier(payload: Any) -> str:
    return stable_identifier("business-workflow", payload)


def business_rule_identifier(payload: Any) -> str:
    return stable_identifier("business-rule", payload)


def business_finding_identifier(payload: Any) -> str:
    return stable_identifier("business-finding", payload)


def business_report_identifier(payload: Any) -> str:
    return stable_identifier("business-report", payload)