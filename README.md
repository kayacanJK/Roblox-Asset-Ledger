# RBX Asset Ledger

**Find and review Roblox asset references before they land in your game.**

RBX Asset Ledger is a small, offline Python CLI for auditing explicit Roblox
asset IDs in Luau scripts and text-based `.rbxlx` / `.rbxmx` exports. It works
without Roblox Studio, network access, or third-party Python dependencies.

It is useful for code review, checking asset inventory before publishing,
and preventing *unreviewed identifiers* from being silently added to a codebase.

> The tool checks references, not asset ownership, content safety, permissions,
> license status, or existence. It never fetches assets and does not inspect
> binary `.rbxl` / `.rbxm` files. This is not a virus scanner.

## Features

- Scans `.lua`, `.luau`, `.rbxlx`, `.rbxmx`, `.json`, `.toml`, `.yaml`, `.yml`.
- Recognizes `rbxassetid://`, Roblox asset URLs, Roblox assetdelivery URLs,
  and `rbxthumb://` URLs containing an asset `id` query parameter.
- Pinpoints every occurrence by relative path, line, and column.
- Catches malformed / zero asset IDs instead of silently ignoring them.
- Produces stable text, JSON, CSV, and Markdown reports.
- Supports reviewed asset allowlists and CI failure on new IDs.
- Skips symlinks, common dependency/cache directories, and oversized files.
- Uses only the Python standard library at runtime (Python 3.10+).

## Install

```bash
python -m pip install -e .
```

Alternatively, clone or download and run directly without installation:

```bash
python -m rbx_asset_ledger ./your-game-project
```

## Quick start

Inventory all references in a Roblox project:

```bash
rbx-asset-ledger ./your-game-project
```

Machine-readable report:

```bash
rbx-asset-ledger ./your-game-project --format json --output asset-report.json
```

A Markdown table for code review:

```bash
rbx-asset-ledger ./your-game-project --format markdown --output asset-report.md
```

Review and approve only assets you trust, using a simple file such as
`approved-assets.txt` (one positive decimal ID per line; `#` starts comments):

```text
# Intentionally allowed audio
123456789
# Approved texture
987654321
```

Then block new, unreviewed references in CI:

```bash
rbx-asset-ledger ./your-game-project --allowlist approved-assets.txt --fail-on-unapproved --fail-on-invalid
```

A build exits with **0** when the enabled checks pass, **2** when a policy check
fails, or **1** on operational errors. Without `--allowlist`, known syntactically
valid IDs are shown as `untracked`, not as `approved`.

## Demo

Try the included example, which intentionally has an invalid reference:

```bash
python -m rbx_asset_ledger examples --allowlist examples/approved-assets.txt --fail-on-invalid
# Exit code: 2 (expected for the deliberately invalid sample)
```

## Output schema

JSON reports are designed for deterministic CI artifact inspection:

```json
{
  "schema_version": 1,
  "summary": {
    "scanned_files": 1,
    "skipped_files": 0,
    "references": 1,
    "unique_asset_ids": 1,
    "invalid_references": 0,
    "unapproved_asset_ids": []
  },
  "references": [
    {
      "path": "src/sound.luau",
      "line": 1,
      "column": 12,
      "asset_id": "123456789",
      "source": "rbxassetid",
      "status": "untracked"
    }
  ],
  "warnings": []
}
```

Actual positions and totals depend on your input files.

## Practical limitations

- Strings in commented-out code are still scanned; this is intentional for a
  lightweight source/text audit, not a Luau parser.
- Numbers in ordinary Lua code are ignored, because they may not be asset IDs.
- Dynamically constructed IDs cannot be inferred.
- Only text-based Roblox exports (`.rbxlx` and `.rbxmx`) are supported.
- Asset ID approval is a **local policy decision**, not verification by Roblox.
- Large files are skipped with a warning (default limit 25 MiB; override with
  `--max-file-mb 100` if needed).
- Files that cannot be read are listed under warnings; inspect warnings in CI.

## Development

```bash
python -m unittest discover -s tests -v
python -m compileall -q rbx_asset_ledger
```

Pull requests should include regression tests for new URL patterns.
See [CONTRIBUTING.md](CONTRIBUTING.md) and [SECURITY.md](SECURITY.md).

## License

MIT. See [LICENSE](LICENSE).
