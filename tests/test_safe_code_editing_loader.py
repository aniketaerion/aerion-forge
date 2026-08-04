from pathlib import Path

import pytest

from forge.safe_code_editing.errors import (
    BinaryFileError,
    FingerprintMismatchError,
    OversizedFileError,
)
from forge.safe_code_editing.identifiers import source_fingerprint
from forge.safe_code_editing.loader import load_text_file
from forge.safe_code_editing.policies import SafeEditPolicy


def test_loader_reads_utf8_and_detects_lf(tmp_path: Path) -> None:
    target = tmp_path / "sample.py"
    target.write_bytes(b"a\nb\n")

    loaded = load_text_file(
        tmp_path,
        "sample.py",
        SafeEditPolicy(),
    )

    assert loaded.content == "a\nb\n"
    assert loaded.newline == "\n"
    assert loaded.fingerprint == source_fingerprint("a\nb\n")


def test_loader_reads_utf8_bom(tmp_path: Path) -> None:
    target = tmp_path / "sample.py"
    target.write_text("hello", encoding="utf-8-sig")

    loaded = load_text_file(
        tmp_path,
        "sample.py",
        SafeEditPolicy(),
    )

    assert loaded.content == "hello"
    assert loaded.encoding == "utf-8-sig"


def test_loader_rejects_binary(tmp_path: Path) -> None:
    target = tmp_path / "binary.bin"
    target.write_bytes(b"abc\x00def")

    with pytest.raises(BinaryFileError):
        load_text_file(
            tmp_path,
            "binary.bin",
            SafeEditPolicy(),
        )


def test_loader_rejects_oversized_file(tmp_path: Path) -> None:
    target = tmp_path / "large.txt"
    target.write_text("abcdef", encoding="utf-8")

    with pytest.raises(OversizedFileError):
        load_text_file(
            tmp_path,
            "large.txt",
            SafeEditPolicy(max_file_bytes=3),
        )


def test_loader_rejects_fingerprint_mismatch(
    tmp_path: Path,
) -> None:
    target = tmp_path / "sample.py"
    target.write_text("current", encoding="utf-8")

    with pytest.raises(FingerprintMismatchError):
        load_text_file(
            tmp_path,
            "sample.py",
            SafeEditPolicy(),
            expected_fingerprint=source_fingerprint("planned"),
        )