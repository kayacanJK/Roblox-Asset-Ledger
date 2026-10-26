"""Immutable scan results and simple reporting semantics."""

from __future__ import annotations

from dataclasses import dataclass, field


@dataclass(frozen=True, order=True)
class Reference:
    path: str
    line: int
    column: int
    asset_id: str
    source: str
    valid: bool

    def status(self, approved_ids: frozenset[str] | None) -> str:
        if not self.valid:
            return "invalid"
        if approved_ids is None:
            return "untracked"
        return "approved" if self.asset_id in approved_ids else "unapproved"

    def as_dict(self, approved_ids: frozenset[str] | None) -> dict[str, object]:
        return {
            "path": self.path,
            "line": self.line,
            "column": self.column,
            "asset_id": self.asset_id,
            "source": self.source,
            "status": self.status(approved_ids),
        }


@dataclass
class ScanResult:
    references: list[Reference] = field(default_factory=list)
    scanned_files: int = 0
    skipped_files: int = 0
    warnings: list[str] = field(default_factory=list)

    @property
    def unique_ids(self) -> int:
        return len({ref.asset_id for ref in self.references if ref.valid})

    def unapproved_ids(self, approved_ids: frozenset[str] | None) -> list[str]:
        if approved_ids is None:
            return []
        return sorted({ref.asset_id for ref in self.references if ref.valid and ref.asset_id not in approved_ids}, key=lambda x: (len(x), x))

    @property
    def invalid_count(self) -> int:
        return sum(not ref.valid for ref in self.references)
