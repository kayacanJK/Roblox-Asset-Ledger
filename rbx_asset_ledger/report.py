"""Deterministic, script-friendly inventory reports."""

from __future__ import annotations

import csv
import io
import json
from collections import defaultdict

from .model import ScanResult

FIELDS = ["path", "line", "column", "asset_id", "source", "status"]


def render(result: ScanResult, fmt: str, approved_ids: frozenset[str] | None = None) -> str:
    rows = [ref.as_dict(approved_ids) for ref in result.references]
    summary = {
        "scanned_files": result.scanned_files,
        "skipped_files": result.skipped_files,
        "references": len(rows),
        "unique_asset_ids": result.unique_ids,
        "invalid_references": result.invalid_count,
        "unapproved_asset_ids": result.unapproved_ids(approved_ids),
    }

    if fmt == "json":
        return json.dumps({"schema_version": 1, "summary": summary, "references": rows, "warnings": result.warnings}, indent=2, ensure_ascii=False) + "\n"
    if fmt == "csv":
        out = io.StringIO(newline="")
        writer = csv.DictWriter(out, fieldnames=FIELDS, lineterminator="\n")
        writer.writeheader()
        writer.writerows(rows)
        return out.getvalue()
    if fmt == "markdown":
        grouped: dict[tuple[str, str], set[str]] = defaultdict(set)
        counts: dict[tuple[str, str], int] = defaultdict(int)
        for row in rows:
            key = (str(row["asset_id"]), str(row["status"]))
            grouped[key].add(str(row["path"]))
            counts[key] += 1
        lines = ["# Roblox asset inventory", "", f"- Files scanned: {result.scanned_files}",
                 f"- References: {len(rows)}", f"- Unique valid IDs: {result.unique_ids}",
                 f"- Invalid references: {result.invalid_count}", "", "| Asset ID | Status | References | Files |", "| --- | --- | ---: | ---: |"]
        for (asset_id, status), paths in sorted(grouped.items(), key=lambda item: (item[0][1], item[0][0])):
            lines.append(f"| {asset_id.replace('|', '')} | {status} | {counts[(asset_id, status)]} | {len(paths)} |")
        if result.warnings:
            lines.extend(["", "## Warnings", ""])
            lines.extend(f"- {warning}" for warning in result.warnings)
        return "\n".join(lines) + "\n"
    if fmt == "text":
        lines = [f"Scanned {result.scanned_files} files; found {len(rows)} references to {result.unique_ids} unique valid asset IDs."]
        if approved_ids is not None:
            lines.append(f"Unapproved IDs: {len(summary['unapproved_asset_ids'])}; invalid references: {result.invalid_count}.")
        elif result.invalid_count:
            lines.append(f"Invalid references: {result.invalid_count}.")
        for row in rows:
            lines.append(f"{row['path']}:{row['line']}:{row['column']}  {row['asset_id'] or '<missing>'}  [{row['status']}, {row['source']}]")
        for warning in result.warnings:
            lines.append(f"WARNING {warning}")
        return "\n".join(lines) + "\n"
    raise ValueError(f"Unsupported output format: {fmt}")
