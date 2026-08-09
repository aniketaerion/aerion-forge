"""Read-only symbol discovery for M5.9 Package 2."""

from __future__ import annotations

import ast
import re
from dataclasses import dataclass

from forge.general_engineering.repository_scanner import ScannedRepositoryFile


@dataclass(frozen=True)
class DiscoveredSymbol:
    name: str
    kind: str
    path: str
    line: int | None


_GENERIC_PATTERNS: tuple[tuple[str, re.Pattern[str]], ...] = (
    ("class", re.compile(r"^\s*(?:export\s+)?class\s+([A-Za-z_$][\w$]*)", re.MULTILINE)),
    (
        "function",
        re.compile(
            r"^\s*(?:export\s+)?(?:async\s+)?function\s+"
            r"([A-Za-z_$][\w$]*)",
            re.MULTILINE,
        ),
    ),
    ("interface", re.compile(r"^\s*(?:export\s+)?interface\s+([A-Za-z_$][\w$]*)", re.MULTILINE)),
    ("type", re.compile(r"^\s*(?:export\s+)?type\s+([A-Za-z_$][\w$]*)\s*=", re.MULTILINE)),
)


def _python_symbols(file: ScannedRepositoryFile) -> tuple[DiscoveredSymbol, ...]:
    try:
        tree = ast.parse(file.content)
    except SyntaxError:
        return ()
    result: list[DiscoveredSymbol] = []
    for node in ast.walk(tree):
        if isinstance(node, ast.ClassDef):
            result.append(DiscoveredSymbol(node.name, "class", file.path, node.lineno))
        elif isinstance(node, ast.AsyncFunctionDef | ast.FunctionDef):
            result.append(DiscoveredSymbol(node.name, "function", file.path, node.lineno))
    return tuple(sorted(result, key=lambda item: (item.line or 0, item.name)))


def discover_symbols(file: ScannedRepositoryFile) -> tuple[DiscoveredSymbol, ...]:
    if file.suffix in {".py", ".pyi"}:
        return _python_symbols(file)

    result: list[DiscoveredSymbol] = []
    for kind, pattern in _GENERIC_PATTERNS:
        for match in pattern.finditer(file.content):
            line = file.content.count("\n", 0, match.start()) + 1
            result.append(DiscoveredSymbol(match.group(1), kind, file.path, line))
    return tuple(sorted(result, key=lambda item: (item.line or 0, item.name)))