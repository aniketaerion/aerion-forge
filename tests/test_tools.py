from pathlib import Path

from forge.tools import FilesystemTool, PowerShellTool


def test_filesystem_tool_reads_but_cannot_escape(tmp_path: Path) -> None:
    (tmp_path / "file.txt").write_text("content", encoding="utf-8")
    tool = FilesystemTool(tmp_path)
    assert tool.execute("read_text", {"path": "file.txt"}).output == "content"
    assert not tool.execute("read_text", {"path": "../outside.txt"}).success


def test_powershell_is_permission_gated(tmp_path: Path) -> None:
    result = PowerShellTool(tmp_path, allowed=False).execute("run", {"command": "Write-Output x"})
    assert not result.success
    assert "disabled" in (result.error or "")
