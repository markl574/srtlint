"""Tests for srtlint.encoding's non-UTF-8 guessing."""

from __future__ import annotations

import unittest

from srtlint.encoding import sniff_encoding

SAMPLE = "1\n00:00:01,000 --> 00:00:02,000\nHello\n"


class SniffEncodingTests(unittest.TestCase):
    def test_utf16_le_bom(self):
        raw = b"\xff\xfe" + SAMPLE.encode("utf-16-le")
        self.assertEqual(sniff_encoding(raw), "utf-16-le")

    def test_utf16_be_bom(self):
        raw = b"\xfe\xff" + SAMPLE.encode("utf-16-be")
        self.assertEqual(sniff_encoding(raw), "utf-16-be")

    def test_utf32_le_bom(self):
        raw = b"\xff\xfe\x00\x00" + SAMPLE.encode("utf-32-le")
        self.assertEqual(sniff_encoding(raw), "utf-32-le")

    def test_utf32_be_bom(self):
        raw = b"\x00\x00\xfe\xff" + SAMPLE.encode("utf-32-be")
        self.assertEqual(sniff_encoding(raw), "utf-32-be")

    def test_utf16_le_without_bom(self):
        raw = SAMPLE.encode("utf-16-le")
        self.assertEqual(sniff_encoding(raw), "utf-16-le")

    def test_utf16_be_without_bom(self):
        raw = SAMPLE.encode("utf-16-be")
        self.assertEqual(sniff_encoding(raw), "utf-16-be")

    def test_windows_1252_accented_text(self):
        raw = "1\n00:00:01,000 --> 00:00:02,000\nCaf\xe9\n".encode("cp1252")
        self.assertEqual(sniff_encoding(raw), "windows-1252")

    def test_garbage_returns_none(self):
        raw = b"\x81\x8d\x90\x9d"
        self.assertIsNone(sniff_encoding(raw))

    def test_plain_ascii_returns_none(self):
        raw = SAMPLE.encode("ascii")
        self.assertIsNone(sniff_encoding(raw))


if __name__ == "__main__":
    unittest.main()
