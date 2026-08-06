from pathlib import Path

import pytest

from forge.domain_intelligence.knowledge_loader.errors import (
    KnowledgeLoaderPolicyError,
)
from forge.domain_intelligence.knowledge_loader.models import (
    KnowledgeLoadRequest,
)
from forge.domain_intelligence.knowledge_loader.policies import (
    KnowledgeLoaderPolicy,
    is_allowed_knowledge_path,
    resolve_knowledge_repository_root,
    validate_knowledge_request,
)


def test_knowledge_loader_policy_is_offline_read_only() -> None:
    policy = KnowledgeLoaderPolicy()

    assert not policy.allow_network
    assert not policy.allow_mutation
    assert not policy.allow_binary_files
    assert not policy.allow_external_paths


def test_knowledge_repository_requires_git(
    tmp_path: Path,
) -> None:
    with pytest.raises(KnowledgeLoaderPolicyError):
        resolve_knowledge_repository_root(
            tmp_path,
            KnowledgeLoaderPolicy(),
        )


def test_knowledge_request_rejects_path_escape() -> None:
    request = KnowledgeLoadRequest(
        repository_root=".",
        project_root="../outside",
    )

    with pytest.raises(KnowledgeLoaderPolicyError):
        validate_knowledge_request(
            request,
            KnowledgeLoaderPolicy(),
        )


def test_allowed_knowledge_path_filters_binary_and_cache(
    tmp_path: Path,
) -> None:
    markdown = tmp_path / "guide.md"
    markdown.write_text("# Guide", encoding="utf-8")

    binary = tmp_path / "firmware.bin"
    binary.write_bytes(b"\x00\x01")

    cache = tmp_path / "__pycache__"
    cache.mkdir()
    cached = cache / "data.json"
    cached.write_text("{}", encoding="utf-8")

    policy = KnowledgeLoaderPolicy()

    assert is_allowed_knowledge_path(
        markdown,
        tmp_path,
        policy,
    )
    assert not is_allowed_knowledge_path(
        binary,
        tmp_path,
        policy,
    )
    assert not is_allowed_knowledge_path(
        cached,
        tmp_path,
        policy,
    )