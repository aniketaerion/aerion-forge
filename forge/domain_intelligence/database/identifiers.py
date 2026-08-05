"""Deterministic identifiers for M4.3 Database Intelligence."""

from __future__ import annotations

from typing import Any

from forge.domain_intelligence.identifiers import stable_identifier


def database_project_identifier(payload: Any) -> str:
    """Return a deterministic database-project identifier."""
    return stable_identifier("database-project", payload)


def database_object_identifier(payload: Any) -> str:
    """Return a deterministic database-object identifier."""
    return stable_identifier("database-object", payload)


def database_finding_identifier(payload: Any) -> str:
    """Return a deterministic database-finding identifier."""
    return stable_identifier("database-finding", payload)


def database_report_identifier(payload: Any) -> str:
    """Return a deterministic database-report identifier."""
    return stable_identifier("database-report", payload)