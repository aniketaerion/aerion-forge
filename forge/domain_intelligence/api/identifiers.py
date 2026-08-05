"""Deterministic identifiers for M4.4 API Domain Intelligence."""

from __future__ import annotations

from typing import Any

from forge.domain_intelligence.identifiers import stable_identifier


def api_project_identifier(payload: Any) -> str:
    """Return a deterministic API-project identifier."""
    return stable_identifier("api-project", payload)


def api_endpoint_identifier(payload: Any) -> str:
    """Return a deterministic API-endpoint identifier."""
    return stable_identifier("api-endpoint", payload)


def api_contract_identifier(payload: Any) -> str:
    """Return a deterministic API-contract identifier."""
    return stable_identifier("api-contract", payload)


def api_finding_identifier(payload: Any) -> str:
    """Return a deterministic API-finding identifier."""
    return stable_identifier("api-finding", payload)


def api_report_identifier(payload: Any) -> str:
    """Return a deterministic API-report identifier."""
    return stable_identifier("api-report", payload)