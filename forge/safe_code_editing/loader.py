"""Safe text-file loading for M3.3."""

from __future__ import annotations

from pathlib import Path

from forge.safe_code_editing.errors import (
    BinaryFileError,
    FingerprintMismatchError,
    OversizedFileError,
    UnsupportedEncodingError,
)
from forge.safe_code_editing.identifiers import source_fingerprint
from forge.safe_code_editing.models import LoadedTextFile
from forge.safe_code_editing.policies import SafeEditPolicy


def _detect_newline(text: str) -> str:
    if "\r\n" in text:
        return "\r\n"
    if "\r" in text:
        return "\r"
    return "\n"


def _decode_text(
    data: bytes,
    allowed_encodings: tuple[str, ...],
) -> tuple[str, str]:
    if b"\x00" in data:
        raise BinaryFileError("binary file detected")

    encodings = list(allowed_encodings)

    if data.startswith(b"\xef\xbb\xbf") and "utf-8-sig" in encodings:
        encodings.remove("utf-8-sig")
        encodings.insert(0, "utf-8-sig")

    for encoding in encodings:
        try:
            return data.decode(encoding), encoding
        except UnicodeDecodeError:
            continue

    raise UnsupportedEncodingError(
        f"unable to decode file with allowed encodings: {allowed_encodings}"
    )


def load_text_file(
    repository_root: Path,
    relative_path: str,
    policy: SafeEditPolicy,
    *,
    expected_fingerprint: str | None = None,
) -> LoadedTextFile:
    """Load a bounded repository text file and verify its fingerprint."""
    path = policy.resolve_path(repository_root, relative_path)

    stat = path.stat()
    if stat.st_size > policy.max_file_bytes:
        raise OversizedFileError(
            f"file exceeds {policy.max_file_bytes} bytes: {relative_path}"
        )

    data = path.read_bytes()
    text, encoding = _decode_text(data, policy.allowed_encodings)
    fingerprint = source_fingerprint(text)

    if (
        expected_fingerprint is not None
        and fingerprint != expected_fingerprint
    ):
        raise FingerprintMismatchError(
            f"source fingerprint mismatch for {relative_path}"
        )

    return LoadedTextFile(
        relative_path=policy.validate_relative_path(relative_path),
        content=text,
        encoding=encoding,
        newline=_detect_newline(text),
        size_bytes=len(data),
        fingerprint=fingerprint,
    )