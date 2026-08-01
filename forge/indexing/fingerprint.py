"""Chunked, bounded, and protected file fingerprinting."""

import hashlib
from pathlib import Path

from forge.indexing.models import FileFingerprint, FingerprintStrategy


class FileFingerprinter:
    """Calculate deterministic SHA-256 fingerprints without unbounded reads."""

    def __init__(self, max_hash_bytes: int, chunk_bytes: int) -> None:
        self.max_hash_bytes = max_hash_bytes
        self.chunk_bytes = chunk_bytes

    def fingerprint(self, path: Path, size: int, sensitive: bool) -> FileFingerprint:
        """Hash a file using full, protected, or bounded-sample handling."""
        strategy = FingerprintStrategy.PROTECTED if sensitive else FingerprintStrategy.FULL
        digest = hashlib.sha256()
        if size <= self.max_hash_bytes:
            with path.open("rb") as stream:
                while chunk := stream.read(self.chunk_bytes):
                    digest.update(chunk)
        else:
            strategy = (
                FingerprintStrategy.PROTECTED_SAMPLED if sensitive else FingerprintStrategy.SAMPLED
            )
            digest.update(f"size:{size}\n".encode())
            with path.open("rb") as stream:
                digest.update(stream.read(self.chunk_bytes))
                stream.seek(max(0, size - self.chunk_bytes))
                digest.update(stream.read(self.chunk_bytes))
        return FileFingerprint(value=digest.hexdigest(), strategy=strategy)

    @staticmethod
    def metadata(size: int, mode: int) -> str:
        """Hash stable non-temporal file metadata."""
        return hashlib.sha256(f"{size}:{mode & 0o777}".encode()).hexdigest()

    @staticmethod
    def is_binary(path: Path, sample_bytes: int = 8192) -> bool:
        """Classify binary files from a bounded prefix without exposing content."""
        with path.open("rb") as stream:
            sample = stream.read(sample_bytes)
        if b"\x00" in sample:
            return True
        try:
            sample.decode("utf-8")
        except UnicodeDecodeError:
            return True
        return False
