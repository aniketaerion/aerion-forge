"""Deterministic identifiers for M4.6 Embedded Domain Intelligence."""

from __future__ import annotations

from typing import Any

from forge.domain_intelligence.identifiers import stable_identifier


def embedded_project_identifier(payload: Any) -> str:
    return stable_identifier("embedded-project", payload)


def embedded_component_identifier(payload: Any) -> str:
    return stable_identifier("embedded-component", payload)


def embedded_interface_identifier(payload: Any) -> str:
    return stable_identifier("embedded-interface", payload)


def embedded_message_identifier(payload: Any) -> str:
    return stable_identifier("embedded-message", payload)


def embedded_finding_identifier(payload: Any) -> str:
    return stable_identifier("embedded-finding", payload)


def embedded_report_identifier(payload: Any) -> str:
    return stable_identifier("embedded-report", payload)