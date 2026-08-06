"""Deterministic identifiers for M4.7 Knowledge Loader Intelligence."""

from __future__ import annotations

from typing import Any

from forge.domain_intelligence.identifiers import stable_identifier


def knowledge_source_identifier(payload: Any) -> str:
    return stable_identifier("knowledge-source", payload)


def knowledge_document_identifier(payload: Any) -> str:
    return stable_identifier("knowledge-document", payload)


def knowledge_chunk_identifier(payload: Any) -> str:
    return stable_identifier("knowledge-chunk", payload)


def knowledge_manifest_identifier(payload: Any) -> str:
    return stable_identifier("knowledge-manifest", payload)


def knowledge_finding_identifier(payload: Any) -> str:
    return stable_identifier("knowledge-finding", payload)


def knowledge_report_identifier(payload: Any) -> str:
    return stable_identifier("knowledge-report", payload)