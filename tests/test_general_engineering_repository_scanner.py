from pathlib import Path

from forge.general_engineering.repository_scanner import scan_repository


def test_scanner_reads_text_and_ignores_git(tmp_path: Path) -> None:
    (tmp_path / "src").mkdir()
    (tmp_path / "src" / "service.py").write_text("VALUE = 1\n", encoding="utf-8")
    (tmp_path / ".git").mkdir()
    (tmp_path / ".git" / "config").write_text("secret\n", encoding="utf-8")

    files = scan_repository(tmp_path)
    assert tuple(item.path for item in files) == ("src/service.py",)
    assert len(files[0].fingerprint) == 64