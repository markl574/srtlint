"""Tests for srtlint.cli, mainly the --format json output."""

from __future__ import annotations

import io
import json
import unittest
from contextlib import redirect_stderr, redirect_stdout
from pathlib import Path
from tempfile import TemporaryDirectory

from srtlint.cli import main

VALID = (
    "1\n"
    "00:00:01,000 --> 00:00:02,000\n"
    "Hello\n"
)

BROKEN = "1\nnot a timing line\nHello\n"

LENIENT_WARNING = (
    "1\n00:00:01,000 --> 00:00:02,000\nHello\n"
    "\n"
    "3\n00:00:03,000 --> 00:00:04,000\nWorld\n"
)


class CliJsonTests(unittest.TestCase):
    def _write(self, dir_path: Path, name: str, content: str) -> Path:
        path = dir_path / name
        path.write_text(content, encoding="utf-8")
        return path

    def test_json_output_for_valid_file(self):
        with TemporaryDirectory() as tmp:
            path = self._write(Path(tmp), "good.srt", VALID)
            out = io.StringIO()
            with redirect_stdout(out):
                code = main(["--format", "json", str(path)])
            self.assertEqual(code, 0)
            payload = json.loads(out.getvalue())
            self.assertEqual(len(payload), 1)
            self.assertEqual(payload[0]["path"], str(path))
            self.assertTrue(payload[0]["ok"])
            self.assertEqual(payload[0]["cues"], 1)
            self.assertEqual(payload[0]["warnings"], [])
            self.assertIsNone(payload[0]["error"])

    def test_json_output_for_broken_file(self):
        with TemporaryDirectory() as tmp:
            path = self._write(Path(tmp), "bad.srt", BROKEN)
            out = io.StringIO()
            with redirect_stdout(out):
                code = main(["--format", "json", str(path)])
            self.assertEqual(code, 1)
            payload = json.loads(out.getvalue())
            self.assertFalse(payload[0]["ok"])
            self.assertIn("malformed timing line", payload[0]["error"])

    def test_json_output_carries_lenient_warnings(self):
        with TemporaryDirectory() as tmp:
            path = self._write(Path(tmp), "warn.srt", LENIENT_WARNING)
            out = io.StringIO()
            with redirect_stdout(out):
                code = main(["--format", "json", "--lenient", str(path)])
            self.assertEqual(code, 0)
            payload = json.loads(out.getvalue())
            self.assertTrue(payload[0]["ok"])
            self.assertTrue(any("expected index 2, got 3" in w for w in payload[0]["warnings"]))

    def test_json_output_covers_multiple_files_in_one_array(self):
        with TemporaryDirectory() as tmp:
            good = self._write(Path(tmp), "good.srt", VALID)
            bad = self._write(Path(tmp), "bad.srt", BROKEN)
            out = io.StringIO()
            with redirect_stdout(out):
                code = main(["--format", "json", str(good), str(bad)])
            self.assertEqual(code, 1)
            payload = json.loads(out.getvalue())
            self.assertEqual(len(payload), 2)
            self.assertTrue(payload[0]["ok"])
            self.assertFalse(payload[1]["ok"])

    def test_text_output_unaffected_by_json_support(self):
        with TemporaryDirectory() as tmp:
            path = self._write(Path(tmp), "good.srt", VALID)
            out = io.StringIO()
            with redirect_stdout(out):
                code = main([str(path)])
            self.assertEqual(code, 0)
            self.assertIn("ok (1 cues)", out.getvalue())

    def test_text_output_error_goes_to_stderr(self):
        with TemporaryDirectory() as tmp:
            path = self._write(Path(tmp), "bad.srt", BROKEN)
            err = io.StringIO()
            with redirect_stderr(err):
                code = main([str(path)])
            self.assertEqual(code, 1)
            self.assertIn("malformed timing line", err.getvalue())


if __name__ == "__main__":
    unittest.main()
