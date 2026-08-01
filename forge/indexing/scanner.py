"""Single-pass current-state repository index scanner."""

import os
from pathlib import Path

from forge.core.repository_policy import EXCLUDED_REPOSITORY_DIRECTORIES
from forge.indexing.classifier import classify_file
from forge.indexing.errors import (
    IndexLimitExceededError,
    IndexPermissionError,
    IndexTargetNotFoundError,
)
from forge.indexing.fingerprint import FileFingerprinter
from forge.indexing.models import (
    FileFingerprint,
    FingerprintStrategy,
    IndexedFile,
    IndexStatus,
)


class ProjectIndexScanner:
    """Traverse once and build portable file records without following symlinks."""

    def __init__(
        self,
        root: Path,
        max_hash_bytes: int,
        chunk_bytes: int,
        max_files: int,
        excluded_files: set[Path] | None = None,
    ) -> None:
        self.root = root.expanduser()
        self.max_files = max_files
        self.fingerprinter = FileFingerprinter(max_hash_bytes, chunk_bytes)
        self.excluded_files = {path.resolve(strict=False) for path in (excluded_files or set())}

    def scan(self) -> tuple[Path, list[IndexedFile]]:
        """Return the validated root and deterministically ordered file records."""
        root = self._validate_root()
        records: list[IndexedFile] = []
        seen = 0
        try:
            for current, directories, filenames in os.walk(root, followlinks=False):
                directories[:] = sorted(
                    directory
                    for directory in directories
                    if directory not in EXCLUDED_REPOSITORY_DIRECTORIES
                    and not (Path(current) / directory).is_symlink()
                )
                for filename in sorted(filenames):
                    seen += 1
                    if seen > self.max_files:
                        raise IndexLimitExceededError(
                            f"Repository exceeds configured file limit of {self.max_files}"
                        )
                    path = Path(current) / filename
                    if path.resolve(strict=False) in self.excluded_files:
                        continue
                    relative = path.relative_to(root).as_posix()
                    records.append(self._record(path, relative))
        except IndexLimitExceededError:
            raise
        except OSError as exc:
            raise IndexPermissionError(f"Unable to traverse repository: {exc}") from exc
        return root, sorted(records, key=lambda item: item.normalized_path)

    def _record(self, path: Path, relative: str) -> IndexedFile:
        classification = classify_file(relative)
        normalized = relative.casefold()
        if path.is_symlink():
            return IndexedFile(
                path=relative,
                normalized_path=normalized,
                file_name=path.name,
                extension=path.suffix.casefold(),
                category=classification.category,
                engineering_role=classification.role,
                repository_area=classification.repository_area,
                size_bytes=0,
                fingerprint=FileFingerprint(strategy=FingerprintStrategy.NONE),
                metadata_fingerprint=FileFingerprinter.metadata(0, 0),
                index_status=IndexStatus.SKIPPED,
                binary=False,
                generated=classification.generated,
                ignored=True,
                manifest=classification.manifest,
                test=classification.test,
                configuration=classification.configuration,
                documentation=classification.documentation,
                migration=classification.migration,
                infrastructure=classification.infrastructure,
                sensitive=classification.sensitive,
                error="symbolic link not followed",
            )
        try:
            stat = path.stat()
            fingerprint = self.fingerprinter.fingerprint(
                path, stat.st_size, classification.sensitive
            )
            binary = self.fingerprinter.is_binary(path)
            status = IndexStatus.INDEXED
            error = None
            size = stat.st_size
            metadata = FileFingerprinter.metadata(stat.st_size, stat.st_mode)
        except OSError:
            fingerprint = FileFingerprint(strategy=FingerprintStrategy.NONE)
            binary = False
            status = IndexStatus.FAILED
            error = "file could not be read"
            size = 0
            metadata = FileFingerprinter.metadata(0, 0)
        return IndexedFile(
            path=relative,
            normalized_path=normalized,
            file_name=path.name,
            extension=path.suffix.casefold(),
            category=classification.category,
            engineering_role=classification.role,
            repository_area=classification.repository_area,
            size_bytes=size,
            fingerprint=fingerprint,
            metadata_fingerprint=metadata,
            index_status=status,
            binary=binary,
            generated=classification.generated,
            ignored=False,
            manifest=classification.manifest,
            test=classification.test,
            configuration=classification.configuration,
            documentation=classification.documentation,
            migration=classification.migration,
            infrastructure=classification.infrastructure,
            sensitive=classification.sensitive,
            error=error,
        )

    def _validate_root(self) -> Path:
        try:
            root = self.root.resolve(strict=True)
        except (OSError, RuntimeError) as exc:
            raise IndexTargetNotFoundError(f"Repository does not exist: {self.root}") from exc
        if not root.is_dir():
            raise IndexTargetNotFoundError(f"Repository is not a directory: {root}")
        if not os.access(root, os.R_OK):
            raise IndexPermissionError(f"Repository is not readable: {root}")
        return root
