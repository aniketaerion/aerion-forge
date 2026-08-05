"""Deterministic identifiers for M4.2 Backend Intelligence."""

from __future__ import annotations

from typing import Any

from forge.domain_intelligence.identifiers import stable_identifier


def backend_project_identifier(payload: Any) -> str:
    """Return a deterministic backend-project identifier."""
    return stable_identifier("backend-project", payload)


def backend_finding_identifier(payload: Any) -> str:
    """Return a deterministic backend-finding identifier."""
    return stable_identifier("backend-finding", payload)


def backend_report_identifier(payload: Any) -> str:
    """Return a deterministic backend-report identifier."""
    return stable_identifier("backend-report", payload)