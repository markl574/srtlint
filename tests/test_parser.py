"""Tests for srtlint.parser covering both strict and lenient paths."""

from __future__ import annotations

import unittest

from srtlint.parser import SubtitleError, parse

VALID = (
    "1\n"
    "00:00:01,000 --> 00:00:02,000\n"
    "Hello\n"
    "\n"
    "2\n"
    "00:00:03,000 --> 00:00:04,000\n"
    "World\n"
)


class StrictModeTests(unittest.TestCase):
    def test_valid_file_parses_with_no_warnings(self):
        cues, warnings = parse(VALID)
        self.assertEqual(len(cues), 2)
        self.assertEqual(warnings, [])
        self.assertEqual(cues[0].start_ms, 1000)
        self.assertEqual(cues[0].end_ms, 2000)
        self.assertEqual(cues[0].text, "Hello")

    def test_empty_file_raises(self):
        with self.assertRaisesRegex(SubtitleError, "no subtitle blocks"):
            parse("")

    def test_bom_raises(self):
        with self.assertRaisesRegex(SubtitleError, "byte-order mark"):
            parse("﻿" + VALID)

    def test_short_block_raises(self):
        content = "1\n00:00:01,000 --> 00:00:02,000\n"
        with self.assertRaisesRegex(SubtitleError, "fewer than 3 lines"):
            parse(content)

    def test_non_sequential_index_raises(self):
        content = (
            "1\n00:00:01,000 --> 00:00:02,000\nHello\n"
            "\n"
            "3\n00:00:03,000 --> 00:00:04,000\nWorld\n"
        )
        with self.assertRaisesRegex(SubtitleError, "expected index 2, got 3"):
            parse(content)

    def test_non_integer_index_raises(self):
        content = "abc\n00:00:01,000 --> 00:00:02,000\nHello\n"
        with self.assertRaisesRegex(SubtitleError, "not an integer"):
            parse(content)

    def test_malformed_timing_line_raises(self):
        content = "1\nnot a timing line\nHello\n"
        with self.assertRaisesRegex(SubtitleError, "malformed timing line"):
            parse(content)

    def test_single_digit_hour_rejected(self):
        content = "1\n1:00:01,000 --> 00:00:02,000\nHello\n"
        with self.assertRaisesRegex(SubtitleError, "malformed timecode"):
            parse(content)

    def test_period_millis_separator_rejected(self):
        content = "1\n00:00:01.000 --> 00:00:02,000\nHello\n"
        with self.assertRaisesRegex(SubtitleError, "malformed timecode"):
            parse(content)

    def test_end_before_start_raises(self):
        content = "1\n00:00:02,000 --> 00:00:01,000\nHello\n"
        with self.assertRaisesRegex(SubtitleError, "end time is not after start time"):
            parse(content)

    def test_start_goes_backwards_raises(self):
        content = (
            "1\n00:00:05,000 --> 00:00:06,000\nHello\n"
            "\n"
            "2\n00:00:01,000 --> 00:00:02,000\nWorld\n"
        )
        with self.assertRaisesRegex(SubtitleError, "start time goes backwards"):
            parse(content)


class LenientModeTests(unittest.TestCase):
    def test_empty_file_returns_no_cues(self):
        cues, warnings = parse("", lenient=True)
        self.assertEqual(cues, [])
        self.assertEqual(warnings, [])

    def test_bom_is_stripped_with_warning(self):
        cues, warnings = parse("﻿" + VALID, lenient=True)
        self.assertEqual(len(cues), 2)
        self.assertTrue(any("byte-order mark" in w for w in warnings))

    def test_short_block_is_skipped_with_warning(self):
        content = "1\n00:00:01,000 --> 00:00:02,000\n"
        cues, warnings = parse(content, lenient=True)
        self.assertEqual(cues, [])
        self.assertTrue(any("fewer than 3 lines" in w for w in warnings))

    def test_non_sequential_index_keeps_actual_index(self):
        content = (
            "1\n00:00:01,000 --> 00:00:02,000\nHello\n"
            "\n"
            "3\n00:00:03,000 --> 00:00:04,000\nWorld\n"
        )
        cues, warnings = parse(content, lenient=True)
        self.assertEqual([c.index for c in cues], [1, 3])
        self.assertTrue(any("expected index 2, got 3" in w for w in warnings))

    def test_non_integer_index_falls_back_to_expected(self):
        content = "abc\n00:00:01,000 --> 00:00:02,000\nHello\n"
        cues, warnings = parse(content, lenient=True)
        self.assertEqual(cues[0].index, 1)
        self.assertTrue(any("not an integer" in w for w in warnings))

    def test_malformed_timing_line_skips_block(self):
        content = (
            "1\nnot a timing line\nHello\n"
            "\n"
            "2\n00:00:03,000 --> 00:00:04,000\nWorld\n"
        )
        cues, warnings = parse(content, lenient=True)
        self.assertEqual(len(cues), 1)
        self.assertEqual(cues[0].index, 2)
        self.assertTrue(any("malformed timing line" in w for w in warnings))

    def test_single_digit_hour_accepted(self):
        content = "1\n1:00:01,000 --> 00:00:02,000\nHello\n"
        cues, warnings = parse(content, lenient=True)
        self.assertEqual(cues[0].start_ms, 3601000)
        self.assertEqual(warnings, [])

    def test_period_millis_separator_accepted(self):
        content = "1\n00:00:01.000 --> 00:00:02,000\nHello\n"
        cues, warnings = parse(content, lenient=True)
        self.assertEqual(cues[0].start_ms, 1000)
        self.assertEqual(warnings, [])

    def test_short_millis_are_padded(self):
        content = "1\n00:00:01,5 --> 00:00:02,000\nHello\n"
        cues, warnings = parse(content, lenient=True)
        self.assertEqual(cues[0].start_ms, 1500)

    def test_end_before_start_is_swapped(self):
        content = "1\n00:00:02,000 --> 00:00:01,000\nHello\n"
        cues, warnings = parse(content, lenient=True)
        self.assertEqual(cues[0].start_ms, 1000)
        self.assertEqual(cues[0].end_ms, 2000)
        self.assertTrue(any("adjusted" in w for w in warnings))

    def test_equal_start_and_end_gets_one_millisecond(self):
        content = "1\n00:00:01,000 --> 00:00:01,000\nHello\n"
        cues, warnings = parse(content, lenient=True)
        self.assertEqual(cues[0].start_ms, 1000)
        self.assertEqual(cues[0].end_ms, 1001)

    def test_start_goes_backwards_keeps_both_cues(self):
        content = (
            "1\n00:00:05,000 --> 00:00:06,000\nHello\n"
            "\n"
            "2\n00:00:01,000 --> 00:00:02,000\nWorld\n"
        )
        cues, warnings = parse(content, lenient=True)
        self.assertEqual(len(cues), 2)
        self.assertTrue(any("goes backwards" in w for w in warnings))


if __name__ == "__main__":
    unittest.main()
