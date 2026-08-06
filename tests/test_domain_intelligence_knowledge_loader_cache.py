from pathlib import Path

from forge.domain_intelligence.knowledge_loader.cache import (
    KnowledgeCache,
)
from forge.domain_intelligence.knowledge_loader.models import (
    KnowledgeLoadReport,
    KnowledgeManifest,
)


def test_knowledge_cache_round_trip(tmp_path: Path) -> None:
    report = KnowledgeLoadReport(
        report_id="knowledge-report-1",
        manifest=KnowledgeManifest(
            manifest_id="knowledge-manifest-1",
            project_root=".",
        ),
    )
    cache = KnowledgeCache(tmp_path)

    path = cache.write(report)
    loaded = cache.read(report.report_id)

    assert path.is_file()
    assert loaded == report