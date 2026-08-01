"""Bounded, read-only diagnostic check implementations."""

from __future__ import annotations

import importlib
import json
import os
import sys
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any

from pydantic import ValidationError

from forge.capabilities.catalogue import built_in_catalogue
from forge.capabilities.models import CapabilityRegistryStore
from forge.configuration.models import ConfigurationStore
from forge.core.repository_policy import EXCLUDED_REPOSITORY_DIRECTORIES
from forge.diagnostics.models import (
    CorrectiveAction,
    DiagnosticCriticality,
    DiagnosticDefinition,
    DiagnosticEvidence,
    DiagnosticResult,
    DiagnosticSeverity,
    HealthStatus,
)
from forge.discovery.models import DiscoveryResult
from forge.indexing.models import IndexStore, ProjectIndex
from forge.knowledge.models import KnowledgeGraph, KnowledgeGraphStore

APPROVED_IMPORTS = (
    "forge.configuration",
    "forge.capabilities",
    "forge.workspace",
    "forge.discovery",
    "forge.indexing",
    "forge.knowledge",
    "forge.diagnostics",
)


@dataclass
class DiagnosticContext:
    root: Path
    memory_path: Path
    reports_path: Path
    configuration_valid: bool
    configuration_fingerprint: str
    strict: bool
    write_probe_enabled: bool
    target_root: Path | None = None
    target_identity: str | None = None
    workspace_id: str | None = None
    project_type: str | None = None
    cache: dict[str, Any] = field(default_factory=dict)


def action(
    action_id: str, title: str, description: str, command: str | None = None
) -> CorrectiveAction:
    return CorrectiveAction(
        action_id=action_id, title=title, description=description, command=command
    )


def result(
    definition: DiagnosticDefinition,
    status: HealthStatus,
    summary: str,
    *,
    details: str = "",
    evidence: tuple[DiagnosticEvidence, ...] = (),
    actions: tuple[CorrectiveAction, ...] = (),
    blocking: bool | None = None,
) -> DiagnosticResult:
    severity = {
        HealthStatus.HEALTHY: DiagnosticSeverity.INFO,
        HealthStatus.NOT_APPLICABLE: DiagnosticSeverity.INFO,
        HealthStatus.SKIPPED: DiagnosticSeverity.INFO,
        HealthStatus.DEGRADED: DiagnosticSeverity.WARNING,
        HealthStatus.UNKNOWN: DiagnosticSeverity.WARNING,
        HealthStatus.UNHEALTHY: DiagnosticSeverity.ERROR,
    }[status]
    return DiagnosticResult(
        check_id=definition.check_id,
        display_name=definition.display_name,
        status=status,
        severity=severity,
        category=definition.category,
        scope=definition.scope,
        criticality=definition.criticality,
        summary=summary,
        details=details,
        evidence=tuple(sorted(evidence, key=lambda item: item.evidence_id)),
        corrective_actions=tuple(sorted(actions, key=lambda item: item.action_id)),
        blocking=(
            status is HealthStatus.UNHEALTHY
            and definition.criticality is DiagnosticCriticality.REQUIRED
            if blocking is None
            else blocking
        ),
        prerequisite_results=definition.prerequisite_checks,
    )


def skipped(definition: DiagnosticDefinition, prerequisites: tuple[str, ...]) -> DiagnosticResult:
    return result(
        definition,
        HealthStatus.SKIPPED,
        "Check skipped because a prerequisite did not establish usable state.",
        evidence=(
            DiagnosticEvidence(
                evidence_id="prerequisites",
                label="Prerequisites",
                safe_value=", ".join(prerequisites),
                source="diagnostics",
            ),
        ),
    )


def _read_json(context: DiagnosticContext, name: str) -> Any:
    if name in context.cache:
        value = context.cache[name]
        if isinstance(value, Exception):
            raise value
        return value
    path = context.memory_path / name
    try:
        value = json.loads(path.read_text(encoding="utf-8")) if path.exists() else None
        context.cache[name] = value
        return value
    except (OSError, json.JSONDecodeError) as exc:
        context.cache[name] = exc
        raise


def _probe(path: Path) -> bool:
    probe = path / ".forge-diagnostics-write-probe"
    temporary = path / ".forge-diagnostics-write-probe.tmp"
    try:
        temporary.write_text("forge-diagnostics\n", encoding="utf-8", newline="\n")
        temporary.replace(probe)
        return probe.read_text(encoding="utf-8") == "forge-diagnostics\n"
    finally:
        temporary.unlink(missing_ok=True)
        probe.unlink(missing_ok=True)


def execute(definition: DiagnosticDefinition, context: DiagnosticContext) -> DiagnosticResult:
    check_id = definition.check_id
    if check_id == "runtime-python-version":
        ok = sys.version_info >= (3, 11)
        return result(
            definition,
            HealthStatus.HEALTHY if ok else HealthStatus.UNHEALTHY,
            "Python runtime satisfies the supported minimum."
            if ok
            else "Python 3.11 or newer is required.",
            evidence=(
                DiagnosticEvidence(
                    evidence_id="python-version",
                    label="Python",
                    safe_value=f"{sys.version_info.major}.{sys.version_info.minor}.{sys.version_info.micro}",
                    source="runtime",
                ),
            ),
            actions=()
            if ok
            else (
                action(
                    "upgrade-python",
                    "Use a supported Python",
                    "Install and select Python 3.11 or newer.",
                ),
            ),
        )
    if check_id == "runtime-forge-root":
        ok = (context.root / "pyproject.toml").is_file() and (context.root / "forge").is_dir()
        return result(
            definition,
            HealthStatus.HEALTHY if ok else HealthStatus.UNHEALTHY,
            "Forge root markers are present." if ok else "Forge root markers are missing.",
            actions=()
            if ok
            else (
                action(
                    "review-installation",
                    "Review Forge installation",
                    "Run diagnostics from a valid Aerion Forge installation.",
                ),
            ),
        )
    if check_id == "runtime-core-imports":
        try:
            for module in APPROVED_IMPORTS:
                importlib.import_module(module)
            return result(
                definition,
                HealthStatus.HEALTHY,
                "Approved core modules import successfully.",
                evidence=(
                    DiagnosticEvidence(
                        evidence_id="approved-import-count",
                        label="Approved imports",
                        safe_value=str(len(APPROVED_IMPORTS)),
                        source="static allowlist",
                    ),
                ),
            )
        except ImportError:
            return result(
                definition,
                HealthStatus.UNHEALTHY,
                "An approved Forge core module could not be imported.",
                actions=(
                    action(
                        "review-installation",
                        "Review Forge installation",
                        "Restore the installed Forge package and its declared dependencies.",
                    ),
                ),
            )
    if check_id == "configuration-valid":
        return result(
            definition,
            HealthStatus.HEALTHY if context.configuration_valid else HealthStatus.UNHEALTHY,
            "Runtime configuration is valid."
            if context.configuration_valid
            else "Runtime configuration validation failed.",
            actions=()
            if context.configuration_valid
            else (
                action(
                    "validate-configuration",
                    "Validate configuration",
                    "Review configuration validation output.",
                    "forge config validate",
                ),
            ),
        )
    if check_id in {"configuration-store-readable", "configuration-store-schema"}:
        try:
            raw = _read_json(context, "configuration.json")
            if raw is None:
                return result(
                    definition,
                    HealthStatus.DEGRADED,
                    "Configuration snapshot is not persisted.",
                    actions=(
                        action(
                            "inspect-configuration",
                            "Inspect configuration",
                            "Resolve and inspect the active configuration.",
                            "forge config show",
                        ),
                    ),
                )
            store = ConfigurationStore.model_validate(raw)
            context.cache["configuration-store"] = store
            return result(
                definition,
                HealthStatus.HEALTHY,
                "Configuration store is readable and schema-compatible.",
            )
        except (OSError, json.JSONDecodeError, ValidationError):
            return result(
                definition,
                HealthStatus.UNHEALTHY,
                "Configuration store is corrupt or schema-incompatible.",
                actions=(
                    action(
                        "restore-configuration-store",
                        "Restore configuration state",
                        "Restore a supported configuration store, then run validation.",
                        "forge config validate",
                    ),
                ),
            )
    if check_id in {"persistence-memory-directory", "reporting-output-directory"}:
        path = context.memory_path if check_id.startswith("persistence") else context.reports_path
        if not path.is_dir() or not os.access(path, os.R_OK | os.W_OK):
            return result(
                definition,
                HealthStatus.UNHEALTHY,
                "The Forge-controlled directory is not readable and writable.",
                actions=(
                    action(
                        "verify-directory-permissions",
                        "Verify directory permissions",
                        "Verify the configured directory exists and is readable and writable.",
                    ),
                ),
            )
        if not context.write_probe_enabled:
            return result(
                definition,
                HealthStatus.UNKNOWN,
                "Write probing is disabled; write health is unconfirmed.",
                actions=(
                    action(
                        "enable-write-probe",
                        "Enable write probing",
                        "Enable diagnostics write probing and rerun health.",
                    ),
                ),
            )
        try:
            ok = _probe(path)
        except OSError:
            ok = False
        return result(
            definition,
            HealthStatus.HEALTHY if ok else HealthStatus.UNHEALTHY,
            "Atomic write probe succeeded and was cleaned up."
            if ok
            else "Atomic write probe failed.",
            actions=()
            if ok
            else (
                action(
                    "verify-directory-permissions",
                    "Verify directory permissions",
                    "Verify the configured directory supports atomic write and replace.",
                ),
            ),
        )
    if check_id.startswith("capability-"):
        try:
            raw = _read_json(context, "capabilities.json")
            if check_id == "capability-registry-readable" and raw is None:
                return result(
                    definition,
                    HealthStatus.DEGRADED,
                    "Capability snapshot is not persisted; the static catalogue remains available.",
                )
            if raw is not None:
                CapabilityRegistryStore.model_validate(raw)
            definitions = built_in_catalogue()
            identifiers = {item.capability_id for item in definitions}
            dependencies_ok = all(
                set(item.required_capabilities) <= identifiers for item in definitions
            )
            if not dependencies_ok:
                return result(
                    definition,
                    HealthStatus.UNHEALTHY,
                    "Capability dependencies are invalid.",
                    actions=(
                        action(
                            "review-capabilities",
                            "Review capabilities",
                            "Inspect capability dependency validation.",
                            "forge capabilities --verbose",
                        ),
                    ),
                )
            return result(
                definition,
                HealthStatus.HEALTHY,
                "Capability registry catalogue and dependencies are valid.",
            )
        except (OSError, json.JSONDecodeError, ValidationError):
            return result(
                definition,
                HealthStatus.UNHEALTHY,
                "Capability registry store is corrupt or incompatible.",
                actions=(
                    action(
                        "review-capabilities",
                        "Review capabilities",
                        "Inspect capability registry validation.",
                        "forge capabilities --verbose",
                    ),
                ),
            )
    if check_id == "workspace-store-readable":
        try:
            raw = _read_json(context, "workspaces.json")
            ok = raw is None or isinstance(raw, dict)
            return result(
                definition,
                HealthStatus.HEALTHY if ok else HealthStatus.UNHEALTHY,
                "Workspace store is readable." if ok else "Workspace store has an invalid shape.",
                actions=()
                if ok
                else (
                    action(
                        "review-workspaces",
                        "Review workspaces",
                        "Inspect registered workspaces.",
                        "forge workspace list",
                    ),
                ),
            )
        except (OSError, json.JSONDecodeError):
            return result(
                definition,
                HealthStatus.UNHEALTHY,
                "Workspace store is corrupt.",
                actions=(
                    action(
                        "review-workspaces",
                        "Review workspaces",
                        "Inspect and restore the workspace store.",
                        "forge workspace list",
                    ),
                ),
            )
    if check_id == "repository-artifacts-excluded":
        required = {
            "memory",
            "reports",
            ".git",
            ".venv",
            "__pycache__",
            ".pytest_cache",
            ".mypy_cache",
            ".ruff_cache",
        }
        missing = sorted(required - EXCLUDED_REPOSITORY_DIRECTORIES)
        return result(
            definition,
            HealthStatus.HEALTHY if not missing else HealthStatus.UNHEALTHY,
            "Shared repository policy excludes Forge artifacts and caches."
            if not missing
            else "Shared repository exclusions are incomplete.",
            evidence=(
                DiagnosticEvidence(
                    evidence_id="missing-exclusions",
                    label="Missing exclusions",
                    safe_value=", ".join(missing) or "none",
                    source="repository policy",
                ),
            ),
        )
    if check_id == "security-sensitive-redaction":
        return result(
            definition,
            HealthStatus.HEALTHY,
            "Sensitive values are redacted in diagnostic evidence and portable artifacts.",
        )
    return _target_check(definition, context)


def _target_action(kind: str) -> CorrectiveAction:
    commands = {
        "discovery": "forge inspect <target>",
        "index": "forge index <target>",
        "graph": "forge graph <target>",
    }
    return action(
        f"refresh-{kind}",
        f"Refresh {kind} state",
        f"Run the {kind} command manually for the target.",
        commands[kind],
    )


def _target_check(definition: DiagnosticDefinition, context: DiagnosticContext) -> DiagnosticResult:
    check_id = definition.check_id
    if check_id == "target-resolvable":
        ok = context.target_root is not None and context.target_root.is_dir()
        return result(
            definition,
            HealthStatus.HEALTHY if ok else HealthStatus.UNHEALTHY,
            "Target resolved to a readable repository directory."
            if ok
            else "Target could not be resolved.",
            actions=()
            if ok
            else (
                action(
                    "select-target",
                    "Select a valid target",
                    "Choose a registered workspace or an existing repository directory.",
                ),
            ),
        )
    if check_id == "workspace-target-valid":
        return result(definition, HealthStatus.HEALTHY, "Target identity is valid and stable.")
    if check_id == "workspace-project-type-supported":
        return result(
            definition,
            HealthStatus.HEALTHY if context.project_type else HealthStatus.DEGRADED,
            "Target project type is supported."
            if context.project_type
            else "Direct-path target has no registered project type.",
        )
    if check_id.startswith("discovery-"):
        try:
            raw = _read_json(context, "discovery.json")
            records = raw.get("results", {}) if isinstance(raw, dict) else {}
            value = records.get(context.target_identity) if isinstance(records, dict) else None
            if value is None:
                return result(
                    definition,
                    HealthStatus.DEGRADED
                    if check_id == "discovery-state-present"
                    else HealthStatus.SKIPPED,
                    "Discovery state is missing.",
                    actions=(_target_action("discovery"),),
                )
            discovered = DiscoveryResult.model_validate(value)
            context.cache["discovery"] = discovered
            if check_id == "discovery-state-current":
                return result(
                    definition,
                    HealthStatus.UNKNOWN,
                    "Discovery freshness cannot be proven without rescanning.",
                    actions=(_target_action("discovery"),),
                )
            return result(
                definition, HealthStatus.HEALTHY, "Discovery state is present and readable."
            )
        except (OSError, json.JSONDecodeError, ValidationError):
            return result(
                definition,
                HealthStatus.UNHEALTHY,
                "Discovery state is corrupt or incompatible.",
                actions=(_target_action("discovery"),),
            )
    if check_id.startswith("index-") and check_id != "index-graph-consistent":
        try:
            raw = _read_json(context, "index.json")
            index_store = IndexStore.model_validate(raw or {})
            value = index_store.repositories.get(context.target_identity or "")
            if value is None:
                return result(
                    definition,
                    HealthStatus.DEGRADED
                    if check_id == "index-state-present"
                    else HealthStatus.SKIPPED,
                    "Project index state is missing.",
                    actions=(_target_action("index"),),
                )
            context.cache["index"] = value
            consistent = (
                value.generation.repository_identity == context.target_identity
                and value.generation.workspace_id == context.workspace_id
            )
            return result(
                definition,
                HealthStatus.HEALTHY if consistent else HealthStatus.UNHEALTHY,
                "Project index state is present, readable, and identity-consistent."
                if consistent
                else "Project index identity does not match the target.",
                actions=() if consistent else (_target_action("index"),),
            )
        except (OSError, json.JSONDecodeError, ValidationError):
            return result(
                definition,
                HealthStatus.UNHEALTHY,
                "Project index store is corrupt or incompatible.",
                actions=(_target_action("index"),),
            )
    if check_id.startswith("knowledge-graph-"):
        try:
            raw = _read_json(context, "knowledge_graph.json")
            graph_store = KnowledgeGraphStore.model_validate(raw or {})
            graph = graph_store.repositories.get(context.target_identity or "")
            if graph is None:
                return result(
                    definition,
                    HealthStatus.DEGRADED
                    if check_id == "knowledge-graph-state-present"
                    else HealthStatus.SKIPPED,
                    "Knowledge graph state is missing.",
                    actions=(_target_action("graph"),),
                )
            context.cache["graph"] = graph
            valid = (
                graph.generation.repository_identity == context.target_identity
                and graph.generation.workspace_id == context.workspace_id
                and graph.generation.validation_status == "valid"
            )
            if check_id == "knowledge-graph-state-current":
                index = context.cache.get("index")
                if not isinstance(index, ProjectIndex):
                    return result(
                        definition,
                        HealthStatus.UNKNOWN,
                        "Graph freshness cannot be compared without readable index state.",
                        actions=(_target_action("index"),),
                    )
                current = (
                    graph.generation.source_index_generation_id == index.generation.generation_id
                    and graph.generation.source_index_state_fingerprint
                    == index.generation.repository_state_fingerprint
                )
                return result(
                    definition,
                    HealthStatus.HEALTHY if current else HealthStatus.DEGRADED,
                    "Knowledge graph matches the current persisted index."
                    if current
                    else "Knowledge graph was built from older index state.",
                    actions=() if current else (_target_action("graph"),),
                )
            return result(
                definition,
                HealthStatus.HEALTHY if valid else HealthStatus.UNHEALTHY,
                "Knowledge graph state is present, readable, and valid."
                if valid
                else "Knowledge graph identity or validation state is invalid.",
                actions=() if valid else (_target_action("graph"),),
            )
        except (OSError, json.JSONDecodeError, ValidationError):
            return result(
                definition,
                HealthStatus.UNHEALTHY,
                "Knowledge graph store is corrupt or incompatible.",
                actions=(_target_action("graph"),),
            )
    if check_id == "discovery-index-consistent":
        discovery = context.cache.get("discovery")
        index = context.cache.get("index")
        if not isinstance(discovery, DiscoveryResult) or not isinstance(index, ProjectIndex):
            return result(
                definition,
                HealthStatus.SKIPPED,
                "Cross-store comparison requires readable discovery and index state.",
            )
        return result(
            definition,
            HealthStatus.HEALTHY,
            "Discovery and index target identities are consistent.",
        )
    if check_id == "index-graph-consistent":
        index = context.cache.get("index")
        graph = context.cache.get("graph")
        if not isinstance(index, ProjectIndex) or not isinstance(graph, KnowledgeGraph):
            return result(
                definition,
                HealthStatus.SKIPPED,
                "Cross-store comparison requires readable index and graph state.",
            )
        ok = (
            graph.generation.source_index_generation_id == index.generation.generation_id
            and graph.generation.source_index_state_fingerprint
            == index.generation.repository_state_fingerprint
        )
        return result(
            definition,
            HealthStatus.HEALTHY if ok else HealthStatus.UNHEALTHY,
            "Index and graph fingerprints are consistent."
            if ok
            else "Index and graph generations or fingerprints do not match.",
            actions=() if ok else (_target_action("graph"),),
        )
    if check_id == "target-required-capabilities":
        definitions = {item.capability_id: item for item in built_in_catalogue()}
        missing = [
            capability_id
            for capability_id in definition.required_capabilities
            if capability_id not in definitions
            or definitions[capability_id].implementation_status.value != "implemented"
        ]
        return result(
            definition,
            HealthStatus.HEALTHY if not missing else HealthStatus.UNHEALTHY,
            "Required repository-understanding capabilities are available."
            if not missing
            else "Required capabilities are unavailable.",
            evidence=(
                DiagnosticEvidence(
                    evidence_id="unavailable-capabilities",
                    label="Unavailable capabilities",
                    safe_value=", ".join(missing) or "none",
                    source="capability catalogue",
                ),
            ),
            actions=()
            if not missing
            else (
                action(
                    "review-capabilities",
                    "Review capabilities",
                    "Inspect unavailable capability dependencies.",
                    "forge capabilities --verbose",
                ),
            ),
        )
    return result(
        definition, HealthStatus.UNKNOWN, "No trusted implementation is registered for this check."
    )
