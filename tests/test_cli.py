import contextlib
import io
import json
import tempfile
import unittest
from pathlib import Path

from rbx_asset_ledger.cli import main


class CliTests(unittest.TestCase):
    def setUp(self):
        self.tempdir = tempfile.TemporaryDirectory()
        self.addCleanup(self.tempdir.cleanup)
        self.root = Path(self.tempdir.name)
        (self.root / "source.luau").write_text('"rbxassetid://100"\n"rbxassetid://abc"\n')
        (self.root / "approved.txt").write_text("100\n")

    def invoke(self, *args):
        stdout, stderr = io.StringIO(), io.StringIO()
        with contextlib.redirect_stdout(stdout), contextlib.redirect_stderr(stderr):
            code = main([str(self.root), *args])
        return code, stdout.getvalue(), stderr.getvalue()

    def test_inventory_is_success_by_default(self):
        code, out, err = self.invoke("--format", "json")
        self.assertEqual(code, 0)
        self.assertEqual(err, "")
        self.assertEqual(json.loads(out)["summary"]["invalid_references"], 1)

    def test_fail_on_invalid(self):
        code, _, _ = self.invoke("--fail-on-invalid")
        self.assertEqual(code, 2)

    def test_fail_on_unapproved(self):
        (self.root / "source.luau").write_text("rbxassetid://101")
        code, _, _ = self.invoke("--allowlist", str(self.root / "approved.txt"), "--fail-on-unapproved")
        self.assertEqual(code, 2)

    def test_valid_approved_id_passes(self):
        (self.root / "source.luau").write_text("rbxassetid://100")
        code, output, _ = self.invoke("--allowlist", str(self.root / "approved.txt"),
                                     "--fail-on-unapproved", "--fail-on-invalid")
        self.assertEqual(code, 0)
        self.assertIn("approved", output)

    def test_report_file(self):
        target = self.root / "reports" / "report.json"
        code, out, _ = self.invoke("--format", "json", "--output", str(target))
        self.assertEqual(code, 0)
        self.assertEqual(out, "")
        self.assertEqual(json.loads(target.read_text())["schema_version"], 1)

    def test_missing_path_returns_one(self):
        err = io.StringIO()
        with contextlib.redirect_stderr(err):
            code = main([str(self.root / "missing")])
        self.assertEqual(code, 1)
        self.assertIn("not found", err.getvalue().lower())

    def test_missing_allowlist_fails_as_argument_error(self):
        with self.assertRaises(SystemExit) as raised:
            with contextlib.redirect_stderr(io.StringIO()):
                main([str(self.root), "--fail-on-unapproved"])
        self.assertEqual(raised.exception.code, 2)

    def test_invalid_allowlist_is_operational_error(self):
        (self.root / "approved.txt").write_text("garbage")
        code, _, err = self.invoke("--allowlist", str(self.root / "approved.txt"))
        self.assertEqual(code, 1)
        self.assertIn("Invalid asset ID", err)

    def test_disable_scan_of_report_files_in_other_formats(self):
        code, out, _ = self.invoke("--exclude", "source.luau")
        self.assertEqual(code, 0)
        self.assertIn("found 0 references", out)


if __name__ == "__main__":
    unittest.main()
