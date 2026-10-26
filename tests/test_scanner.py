import json
import tempfile
import unittest
from pathlib import Path

from rbx_asset_ledger.policy import load_allowlist
from rbx_asset_ledger.report import render
from rbx_asset_ledger.scanner import scan


class ScannerTests(unittest.TestCase):
    def setUp(self):
        self.tempdir = tempfile.TemporaryDirectory()
        self.addCleanup(self.tempdir.cleanup)
        self.root = Path(self.tempdir.name)

    def write(self, name, content):
        path = self.root / name
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(content, encoding="utf-8")
        return path

    def test_find_luau_and_roblox_xml_references(self):
        self.write("src/a.luau", 'print("rbxassetid://12345")\n')
        self.write("world.rbxlx", '<url>https://www.roblox.com/asset/?id=12345</url>\n')
        found = scan(self.root)
        self.assertEqual(found.scanned_files, 2)
        self.assertEqual(found.unique_ids, 1)
        self.assertEqual(len(found.references), 2)
        self.assertEqual([r.path for r in found.references], ["src/a.luau", "world.rbxlx"])

    def test_malformed_and_zero_ids(self):
        self.write("a.lua", '"rbxassetid://bad"\n"rbxassetid://0"\n"rbxassetid://"\n')
        found = scan(self.root)
        self.assertEqual(found.invalid_count, 3)
        self.assertEqual(found.unique_ids, 0)
        self.assertTrue(all(not r.valid for r in found.references))

    def test_normalizes_leading_zeros(self):
        self.write("a.luau", '"rbxassetid://000123"')
        found = scan(self.root)
        self.assertEqual(found.references[0].asset_id, "123")

    def test_assetdelivery_and_thumbnail_urls(self):
        self.write("a.luau", '"https://assetdelivery.roblox.com/v1/asset/?id=43"\n"rbxthumb://type=Asset&id=52&w=150&h=150"')
        found = scan(self.root)
        self.assertEqual([(r.asset_id, r.source) for r in found.references],
                         [("43", "assetdelivery-url"), ("52", "rbxthumb")])

    def test_non_roblox_urls_and_plain_numbers_ignored(self):
        self.write("x.luau", 'local count = 1234\nlocal url = "https://example.org/asset/?id=1234"\n')
        self.assertEqual(scan(self.root).references, [])

    def test_line_column_and_sorted_results(self):
        self.write("b.lua", 'foo = "rbxassetid://12"\n')
        self.write("a.luau", '"rbxassetid://10" "rbxassetid://11"')
        found = scan(self.root)
        self.assertEqual([(r.path, r.line, r.column) for r in found.references],
                         [("a.luau", 1, 2), ("a.luau", 1, 20), ("b.lua", 1, 8)])

    def test_skip_unrelated_extensions_and_git_dir(self):
        self.write("notes.md", "rbxassetid://55")
        self.write(".git/config.luau", "rbxassetid://44")
        self.write("main.luau", "rbxassetid://33")
        found = scan(self.root)
        self.assertEqual([r.asset_id for r in found.references], ["33"])

    def test_exclusion_globs(self):
        self.write("generated/cached.luau", "rbxassetid://888")
        self.write("src/code.luau", "rbxassetid://123")
        found = scan(self.root, excludes=("generated/*",))
        self.assertEqual([r.asset_id for r in found.references], ["123"])

    def test_skip_large_file_with_warning(self):
        self.write("big.luau", "rbxassetid://1234" * 5)
        found = scan(self.root, max_file_bytes=10)
        self.assertEqual(found.skipped_files, 1)
        self.assertTrue(found.warnings)
        self.assertEqual(found.references, [])

    def test_scan_specific_file(self):
        path = self.write("folder/hello.luau", "rbxassetid://321")
        found = scan(path)
        self.assertEqual(found.references[0].path, "hello.luau")

    def test_policy_approval_and_deduplication(self):
        self.write("a.luau", '"rbxassetid://123" "rbxassetid://123" "rbxassetid://456"')
        found = scan(self.root)
        self.assertEqual(found.unapproved_ids(frozenset({"123"})), ["456"])
        statuses = [r.status(frozenset({"123"})) for r in found.references]
        self.assertEqual(statuses, ["approved", "approved", "unapproved"])

    def test_empty_allowlist_rejects_all_not_silently_untracked(self):
        self.write("a.luau", "rbxassetid://12")
        found = scan(self.root)
        self.assertEqual(found.unapproved_ids(frozenset()), ["12"])

    def test_allowlist_comments_and_zero_padding(self):
        file = self.write("approved.txt", "# known assets\n00012 # sound\n\n34\n")
        self.assertEqual(load_allowlist(file), frozenset({"12", "34"}))

    def test_allowlist_rejects_invalid_tokens(self):
        file = self.write("approved.txt", "123\nnope\n")
        with self.assertRaisesRegex(ValueError, "line 2"):
            load_allowlist(file)

    def test_json_schema_and_markdown_rendering(self):
        self.write("a.luau", '"rbxassetid://123"')
        found = scan(self.root)
        data = json.loads(render(found, "json"))
        self.assertEqual(data["schema_version"], 1)
        self.assertEqual(data["references"][0]["status"], "untracked")
        self.assertIn("| Asset ID |", render(found, "markdown"))

    def test_csv_output_with_header(self):
        self.write("a.luau", '"rbxassetid://123"')
        value = render(scan(self.root), "csv")
        self.assertIn("path,line,column,asset_id,source,status", value)
        self.assertIn("a.luau,1,2,123,rbxassetid,untracked", value)

    def test_nonexistent_path_is_error(self):
        with self.assertRaises(ValueError):
            scan(self.root / "missing")

    @unittest.skipUnless(hasattr(Path, "symlink_to"), "symlink unavailable")
    def test_symlinked_file_not_followed(self):
        original = self.write("external.lua", "rbxassetid://456")
        link = self.root / "link.luau"
        try:
            link.symlink_to(original)
        except OSError:
            self.skipTest("symlink privileges unavailable")
        found = scan(self.root)
        self.assertEqual([r.path for r in found.references], ["external.lua"])


if __name__ == "__main__":
    unittest.main()
