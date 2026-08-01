"""Portable canonical graph identity helpers."""

import hashlib

from forge.knowledge.models import KnowledgeEdgeType, KnowledgeNodeType


def normalize_path(path: str) -> str:
    """Normalize separators and case consistently across operating systems."""
    return "/".join(part for part in path.replace("\\", "/").split("/") if part).casefold()


def node_id(node_type: KnowledgeNodeType, identity: str, name: str = "") -> str:
    """Build a stable human-readable canonical node ID."""
    if node_type in {KnowledgeNodeType.WORKSPACE, KnowledgeNodeType.REPOSITORY}:
        return f"{node_type.value}:{identity.casefold()}"
    canonical = normalize_path(name) if name else identity.casefold()
    if node_type in {
        KnowledgeNodeType.LANGUAGE,
        KnowledgeNodeType.FRAMEWORK,
        KnowledgeNodeType.PACKAGE_MANAGER,
        KnowledgeNodeType.BUILD_SYSTEM,
        KnowledgeNodeType.TEST_FRAMEWORK,
        KnowledgeNodeType.DATABASE,
        KnowledgeNodeType.DEPENDENCY,
    }:
        return f"{node_type.value}:{canonical}"
    return f"{node_type.value}:{identity}:{canonical}" if name else f"{node_type.value}:{identity}"


def edge_id(source: str, edge_type: KnowledgeEdgeType, target: str) -> str:
    """Hash one canonical directional relationship."""
    value = f"{source}|{edge_type.value}|{target}"
    return f"edge:{hashlib.sha256(value.encode()).hexdigest()}"
