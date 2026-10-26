"""Read-only scanning of source files and text-based Roblox place/model exports.

No Roblox API calls are made. Findings are syntactic references only; they do
not imply an asset is public, owned, malicious, or even available.
"""

from __future__ import annotations

import fnmatch
import os
import re
from pathlib import Path
from typing import Iterator

from .model import Reference, ScanResult

EXTENSIONS = frozenset({".lua", ".luau", ".rbxlx", ".rbxmx", ".json", ".toml", ".yaml", ".yml"})
SKIP_DIRS = frozenset({".git", ".hg", ".svn", ".venv", "venv", "node_modules", "__pycache__", ".mypy_cache", ".pytest_cache"})
DEFAULT_MAX_BYTES = 25 * 1024 * 1024

# Match the explicit Roblox reference forms, not arbitrary numeric literals.
# URI capture deliberately includes malformed tokens to report them.
_PATTERNS = (
    ("rbxassetid", re.compile(r"(?i)(?<![a-z0-9_])rbxassetid://(?P<id>[a-z0-9_-]*)")),
    ("roblox-asset-url", re.compile(r"(?i)https?://(?:www\.)?roblox\.com/asset/\?[^\s\"'<>)]*?\bid=(?P<id>[a-z0-9_-]*)")),
    ("assetdelivery-url", re.compile(r"(?i)https?://assetdelivery\.roblox\.com/v1/asset/\?[^\s\"'<>)]*?\bid=(?P<id>[a-z0-9_-]*)")),
    ("rbxthumb", re.compile(r"(?i)(?<![a-z0-9_])rbxthumb://[^\s\"'<>)]*?\bid=(?P<id>[a-z0-9_-]*)")),
)


def _normalize(token: str) -> tuple[str, bool]:
    if not token.isascii() or not token.isdecimal():
        return token, False
    number = int(token)
    if number <= 0:
        return token, False
    return str(number), True


def _iter_files(root: Path, excludes: tuple[str, ...]) -> Iterator[Path]:
    if root.is_file():
        if not root.is_symlink() and root.suffix.lower() in EXTENSIONS:
            yield root
        return

    for current_dir, dirs, names in os.walk(root, followlinks=False):
        current = Path(current_dir)
        dirs[:] = sorted(d for d in dirs if d not in SKIP_DIRS and not (current / d).is_symlink()
                         and not _excluded((current / d).relative_to(root).as_posix(), excludes))
        for name in sorted(names):
            path = current / name
            if path.is_symlink() or path.suffix.lower() not in EXTENSIONS:
                continue
            if _excluded(path.relative_to(root).as_posix(), excludes):
                continue
            yield path


def _excluded(relative_path: str, patterns: tuple[str, ...]) -> bool:
    return any(fnmatch.fnmatchcase(relative_path, pattern) for pattern in patterns)


def scan(root: Path, *, max_file_bytes: int = DEFAULT_MAX_BYTES, excludes: tuple[str, ...] = ()) -> ScanResult:
    if not root.exists():
        raise ValueError(f"Path not found: {root}")
    if root.is_symlink():
        raise ValueError("Refusing to scan a symlink as the root path")
    if max_file_bytes < 1:
        raise ValueError("max_file_bytes must be positive")
    if not root.is_dir() and not root.is_file():
        raise ValueError(f"Not a regular file or directory: {root}")

    result = ScanResult()
    for path in _iter_files(root, excludes):
        relative = path.relative_to(root).as_posix() if root.is_dir() else path.name
        try:
            if path.stat().st_size > max_file_bytes:
                result.skipped_files += 1
                result.warnings.append(f"{relative}: larger than max file size")
                continue
            # newline='' preserves line breaks; text replaces malformed UTF-8.
            with path.open("r", encoding="utf-8-sig", errors="replace", newline="") as handle:
                for line_number, line in enumerate(handle, 1):
                    hits: list[Reference] = []
                    for source, pattern in _PATTERNS:
                        for match in pattern.finditer(line):
                            asset_id, valid = _normalize(match.group("id"))
                            hits.append(Reference(relative, line_number, match.start() + 1, asset_id, source, valid))
                    hits.sort(key=lambda ref: (ref.column, ref.source))
                    result.references.extend(hits)
            result.scanned_files += 1
        except (OSError, UnicodeError) as exc:
            result.skipped_files += 1
            result.warnings.append(f"{relative}: could not read ({type(exc).__name__})")

    result.references.sort(key=lambda ref: (ref.path, ref.line, ref.column, ref.source))
    return result
