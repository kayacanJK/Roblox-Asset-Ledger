"""Small, deliberately explicit allowlist format.

An allowlist only establishes *project approval*, not asset safety or ownership.
"""

from __future__ import annotations

from pathlib import Path


def load_allowlist(path: Path) -> frozenset[str]:
    try:
        lines = path.read_text(encoding="utf-8-sig").splitlines()
    except OSError as exc:
        raise ValueError(f"Cannot read allowlist: {path} ({exc})") from exc
    approved: set[str] = set()
    for number, line in enumerate(lines, 1):
        token = line.split("#", 1)[0].strip()
        if not token:
            continue
        if not token.isascii() or not token.isdecimal() or int(token) <= 0:
            raise ValueError(f"Invalid asset ID in {path} on line {number}: {token!r}")
        approved.add(str(int(token)))
    return frozenset(approved)
