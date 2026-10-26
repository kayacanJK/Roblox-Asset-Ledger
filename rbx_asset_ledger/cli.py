"""Command-line interface and exit-code policy."""

from __future__ import annotations

import argparse
import sys
from pathlib import Path

from .policy import load_allowlist
from .report import render
from .scanner import DEFAULT_MAX_BYTES, scan


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        prog="rbx-asset-ledger",
        description="Inventory explicit Roblox asset references without internet access or Studio."
    )
    parser.add_argument("path", nargs="?", default=".", help="Directory or supported file to scan (default: current directory)")
    parser.add_argument("--format", choices=("text", "json", "csv", "markdown"), default="text", help="Report format")
    parser.add_argument("--output", type=Path, help="Write a report to a file instead of stdout")
    parser.add_argument("--allowlist", type=Path, help="Text file with one approved asset ID per line")
    parser.add_argument("--fail-on-unapproved", action="store_true", help="Exit 2 for an ID not in --allowlist")
    parser.add_argument("--fail-on-invalid", action="store_true", help="Exit 2 for malformed rbxassetid/asset URLs")
    parser.add_argument("--exclude", action="append", default=[], metavar="GLOB", help="Exclude a relative path pattern; may be repeated")
    parser.add_argument("--max-file-mb", type=int, default=DEFAULT_MAX_BYTES // (1024 * 1024), metavar="N", help="Maximum input file size in MiB (default: 25)")
    return parser


def main(argv: list[str] | None = None) -> int:
    parser = build_parser()
    args = parser.parse_args(argv)
    if args.fail_on_unapproved and args.allowlist is None:
        parser.error("--fail-on-unapproved requires --allowlist")
    if args.max_file_mb < 1:
        parser.error("--max-file-mb must be positive")
    try:
        approved = load_allowlist(args.allowlist) if args.allowlist is not None else None
        result = scan(Path(args.path), max_file_bytes=args.max_file_mb * 1024 * 1024,
                      excludes=tuple(args.exclude))
        report = render(result, args.format, approved)
        if args.output:
            args.output.parent.mkdir(parents=True, exist_ok=True)
            args.output.write_text(report, encoding="utf-8")
        else:
            sys.stdout.write(report)
    except (OSError, ValueError) as exc:
        print(f"Error: {exc}", file=sys.stderr)
        return 1
    if args.fail_on_invalid and result.invalid_count:
        return 2
    if args.fail_on_unapproved and result.unapproved_ids(approved):
        return 2
    return 0
