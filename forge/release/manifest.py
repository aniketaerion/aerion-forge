"""Deterministic Phase 1 release manifest construction."""

import hashlib
import json

from forge.capabilities.catalogue import built_in_catalogue
from forge.capabilities.models import CapabilityImplementationStatus
from forge.release.models import (
    PhaseReleaseManifest,
    PhaseSchemaEntry,
    ReleaseDecision,
)

SCHEMAS = (
    PhaseSchemaEntry(
        subsystem="workspace",
        schema_version="legacy-1.0",
        persistence_file="memory/workspaces.json",
        primary_models=("Workspace", "ProjectType"),
        compatibility_policy=(
            "Additive fields only within v0.2; migration required for breaking changes."
        ),
    ),
    PhaseSchemaEntry(
        subsystem="discovery",
        schema_version="legacy-1.0",
        persistence_file="memory/discovery.json",
        primary_models=("DiscoveryResult",),
        compatibility_policy=(
            "Additive fields only within v0.2; migration required for breaking changes."
        ),
    ),
    PhaseSchemaEntry(
        subsystem="index",
        schema_version="1.0",
        persistence_file="memory/index.json",
        primary_models=("IndexStore", "ProjectIndex", "IndexGeneration"),
        compatibility_policy="Schema mismatch is explicit; breaking changes require migration.",
    ),
    PhaseSchemaEntry(
        subsystem="knowledge_graph",
        schema_version="1.0",
        persistence_file="memory/knowledge_graph.json",
        primary_models=("KnowledgeGraphStore", "KnowledgeGraph", "KnowledgeGraphGeneration"),
        compatibility_policy="Schema mismatch is explicit; breaking changes require migration.",
    ),
    PhaseSchemaEntry(
        subsystem="capabilities",
        schema_version="1.0",
        persistence_file="memory/capabilities.json",
        primary_models=("CapabilityRegistryStore", "CapabilityRegistry"),
        compatibility_policy="Schema mismatch is explicit; breaking changes require migration.",
    ),
    PhaseSchemaEntry(
        subsystem="configuration",
        schema_version="1.0",
        persistence_file="memory/configuration.json",
        primary_models=("ConfigurationStore", "ConfigurationSnapshot"),
        compatibility_policy="Schema mismatch is explicit; breaking changes require migration.",
    ),
    PhaseSchemaEntry(
        subsystem="diagnostics",
        schema_version="1.0",
        persistence_file="memory/diagnostics.json",
        primary_models=("DiagnosticStore", "DiagnosticSnapshot"),
        compatibility_policy="Schema mismatch is explicit; breaking changes require migration.",
    ),
)


def build_release_manifest() -> PhaseReleaseManifest:
    """Build the immutable, Git-independent release evidence model."""
    catalogue = built_in_catalogue()
    implemented = tuple(
        sorted(
            item.capability_id
            for item in catalogue
            if item.implementation_status is CapabilityImplementationStatus.IMPLEMENTED
        )
    )
    planned = tuple(
        sorted(
            item.capability_id
            for item in catalogue
            if item.implementation_status is CapabilityImplementationStatus.NOT_IMPLEMENTED
        )
    )
    return PhaseReleaseManifest(
        product="Aerion Forge",
        version="0.2.0",
        phase="1",
        milestone="1.8",
        release_name="Engineering Runtime",
        baseline_commit="7e3879d",
        baseline_tag="forge-v0.2-m1.7",
        release_commit="pending",
        schemas=SCHEMAS,
        implemented_capability_ids=implemented,
        planned_capability_ids=planned,
        test_count=151,
        source_file_count=137,
        validation={
            "git_diff_check": "passed",
            "mypy": "passed",
            "pytest": "passed",
            "ruff": "passed",
        },
        frozen_contracts=(
            "capability-registry",
            "diagnostics",
            "discovery",
            "indexing",
            "knowledge-graph",
            "repository-policy",
            "runtime-configuration",
            "workspace",
        ),
        persistence_files=tuple(item.persistence_file for item in SCHEMAS),
        report_families=(
            "capabilities",
            "configuration",
            "diagnostics",
            "discovery",
            "index",
            "knowledge_graph",
            "release",
        ),
        cli_command_families=(
            "capabilities",
            "capability",
            "config",
            "diagnose",
            "graph",
            "health",
            "index",
            "inspect",
            "workspace",
        ),
        security_status="passed",
        determinism_status="passed",
        compatibility_status="passed",
        release_decision=ReleaseDecision.CONDITIONAL_PASS,
        recommended_commit="release: complete Aerion Forge v0.2 engineering runtime",
        recommended_tag="forge-v0.2.0",
    )


def render_release_manifest(manifest: PhaseReleaseManifest | None = None) -> str:
    """Render canonical deterministic JSON with a trailing newline."""
    value = manifest or build_release_manifest()
    return json.dumps(value.model_dump(mode="json"), indent=2, sort_keys=True) + "\n"


def release_manifest_fingerprint(manifest: PhaseReleaseManifest | None = None) -> str:
    return hashlib.sha256(render_release_manifest(manifest).encode("utf-8")).hexdigest()
