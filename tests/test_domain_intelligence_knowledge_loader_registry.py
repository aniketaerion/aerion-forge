from forge.domain_intelligence.knowledge_loader.models import (
    KnowledgeSourceKind,
)
from forge.domain_intelligence.knowledge_loader.registry import (
    KnowledgeLoaderRegistry,
)


def test_default_knowledge_loader_registry() -> None:
    registry = KnowledgeLoaderRegistry.default()

    assert KnowledgeSourceKind.MARKDOWN in registry.kinds()
    assert KnowledgeSourceKind.JSON in registry.kinds()
    assert KnowledgeSourceKind.PYTHON in registry.kinds()