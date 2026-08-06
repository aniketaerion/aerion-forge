from pathlib import Path

import pytest

from forge.domain_intelligence.knowledge_loader.errors import (
    KnowledgeLoaderPolicyError,
)
from forge.domain_intelligence.knowledge_loader.resolver import (
    resolve_knowledge_project_root,
)


def test_knowledge_project_root_resolution(
    tmp_path: Path,
) -> None:
    docs = tmp_path / "docs"
    docs.mkdir()

    assert resolve_knowledge_project_root(
        tmp_path,
        "docs",
    ) == docs.resolve()


def test_knowledge_project_root_rejects_escape(
    tmp_path: Path,
) -> None:
    with pytest.raises(KnowledgeLoaderPolicyError):
        resolve_knowledge_project_root(
            tmp_path,
            "../outside",
        )