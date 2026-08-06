"""Deterministic identifiers for M4.8 Phase Validation Intelligence."""

from __future__ import annotations

from typing import Any

from forge.domain_intelligence.identifiers import stable_identifier


def phase_validation_check_identifier(payload: Any) -> str:
    return stable_identifier("phase-validation-check", payload)


def phase_validation_result_identifier(payload: Any) -> str:
    return stable_identifier("phase-validation-result", payload)


def phase_validation_finding_identifier(payload: Any) -> str:
    return stable_identifier("phase-validation-finding", payload)


def phase_validation_report_identifier(payload: Any) -> str:
    return stable_identifier("phase-validation-report", payload)


def phase_release_manifest_identifier(payload: Any) -> str:
    return stable_identifier("phase-release-manifest", payload)