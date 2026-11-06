"""Tests for scripts.sdlc.scan_text."""

import contextlib
import io
import tempfile
import unittest
from pathlib import Path

from scripts.sdlc import scan_text

PHONE = "0171" + "2345678"


def run(*args):
    out, err = io.StringIO(), io.StringIO()
    with contextlib.redirect_stdout(out), contextlib.redirect_stderr(err):
        code = scan_text.main(list(args))
    return code, out.getvalue(), err.getvalue()


class TestScanText(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.root = Path(self.tmp.name)
        self.addCleanup(self.tmp.cleanup)

    def write(self, rel, text):
        path = self.root / rel
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(text, encoding="utf-8")
        return path

    def test_clean_files_pass(self):
        self.write("m/a.md", "# Mockup\nFake patient Asha, age 30\n")
        code, out, _ = run(str(self.root / "m"))
        self.assertEqual(code, 0)
        self.assertIn("No sensitive data", out)

    def test_finding_reports_file_line_category_but_not_value(self):
        path = self.write("m/a.html", f"<p>ok</p>\n<p>call {PHONE}</p>\n")
        code, out, _ = run(str(self.root / "m"))
        self.assertEqual(code, 1)
        self.assertIn(f"{path}:2: bd_phone", out)
        self.assertNotIn(PHONE, out)

    def test_missing_directory_is_skipped(self):
        self.assertEqual(run(str(self.root / "nope"))[0], 0)

    def test_non_text_suffix_ignored(self):
        self.write("m/a.bin", PHONE)
        self.assertEqual(run(str(self.root / "m"))[0], 0)

    def test_covers_all_text_suffixes(self):
        for suffix in ("md", "html", "svg", "txt", "json", "csv"):
            self.write(f"m/x.{suffix}", PHONE)
        findings = scan_text.scan_dirs([self.root / "m"])
        self.assertEqual(len(findings), 6)

    def test_no_args_is_usage_error(self):
        self.assertEqual(run()[0], 2)


if __name__ == "__main__":
    unittest.main()
