import logging
from pathlib import Path

from forge.discovery.service import DiscoveryService
from forge.indexing import IndexConfiguration
from forge.indexing.service import IndexingService
from forge.indexing.store import ProjectIndexStore
from forge.knowledge import KnowledgeGraphConfiguration
from forge.knowledge.service import KnowledgeGraphService
from forge.knowledge.store import KnowledgeGraphRepository
from forge.memory import JsonMemoryStore


def logger_for(name: str) -> logging.Logger:
    logger = logging.getLogger(name)
    logger.handlers = [logging.NullHandler()]
    return logger


def write(path: Path, content: str = "content") -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(content, encoding="utf-8")


def prepare_inputs(base: Path, repository: Path, workspace_id: str | None = None) -> None:
    logger = logger_for(f"inputs-{base.name}")
    DiscoveryService(
        JsonMemoryStore(base / "memory" / "discovery.json"),
        base / "reports",
        logger,
    ).inspect(repository, workspace_id)
    IndexingService(
        ProjectIndexStore(base / "memory" / "index.json"),
        base / "reports",
        logger,
        IndexConfiguration(
            max_hash_bytes=1024 * 1024,
            hash_chunk_bytes=1024,
            max_files=10_000,
        ),
    ).index(repository, workspace_id)


def graph_service(
    base: Path,
    max_nodes: int = 100_000,
    include_directories: bool = True,
) -> KnowledgeGraphService:
    return KnowledgeGraphService(
        base / "memory" / "discovery.json",
        ProjectIndexStore(base / "memory" / "index.json"),
        KnowledgeGraphRepository(base / "memory" / "knowledge_graph.json"),
        base / "reports",
        logger_for(f"graph-{base.name}"),
        KnowledgeGraphConfiguration(
            max_nodes=max_nodes,
            max_edges=300_000,
            max_module_depth=2,
            include_directory_nodes=include_directories,
        ),
    )
