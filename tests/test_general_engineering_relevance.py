from forge.general_engineering.relevance import score_file_relevance
from forge.general_engineering.repository_scanner import ScannedRepositoryFile
from forge.general_engineering.symbol_discovery import discover_symbols


def test_relevance_prefers_matching_repository_evidence() -> None:
    relevant = ScannedRepositoryFile(
        path="src/invoice_service.py",
        size_bytes=30,
        suffix=".py",
        fingerprint="a",
        content="def approve_invoice():\n    pass\n",
    )
    unrelated = ScannedRepositoryFile(
        path="src/logger.py",
        size_bytes=20,
        suffix=".py",
        fingerprint="b",
        content="def log_event():\n    pass\n",
    )
    a = score_file_relevance("Approve invoice", relevant, discover_symbols(relevant))
    b = score_file_relevance("Approve invoice", unrelated, discover_symbols(unrelated))
    assert a.score > b.score