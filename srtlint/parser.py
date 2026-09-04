"""Parsing and structural validation for SRT subtitle files."""

from __future__ import annotations

import re
from dataclasses import dataclass

# Strict mode requires exactly HH:MM:SS,mmm. Lenient mode also accepts a
# single-digit hour and a period instead of a comma before the milliseconds,
# both of which show up constantly in subtitles exported by older tools.
TIMECODE_STRICT = re.compile(r"^(\d{2}):(\d{2}):(\d{2}),(\d{3})$")
TIMECODE_LENIENT = re.compile(r"^(\d{1,2}):(\d{2}):(\d{2})[,.](\d{1,3})$")


class SubtitleError(Exception):
    """Raised when a subtitle file breaks the format in a way we won't guess around."""


@dataclass
class Cue:
    index: int
    start_ms: int
    end_ms: int
    text: str
    line: int


def _parse_timecode(raw: str, lenient: bool, line_no: int) -> int:
    pattern = TIMECODE_LENIENT if lenient else TIMECODE_STRICT
    match = pattern.match(raw.strip())
    if not match:
        raise SubtitleError(f"line {line_no}: malformed timecode {raw!r}")
    hours, minutes, seconds, millis = match.groups()
    millis = millis.ljust(3, "0")
    total = ((int(hours) * 3600 + int(minutes) * 60 + int(seconds)) * 1000) + int(millis)
    return total


def parse(content: str, lenient: bool = False) -> tuple[list[Cue], list[str]]:
    """Parse SRT text into cues.

    In strict mode the first structural problem raises SubtitleError. In
    lenient mode we recover where there's an obvious, unambiguous fix and
    collect a warning instead; only unrecoverable garbage still raises.
    """
    warnings: list[str] = []

    if content.startswith("﻿"):
        if not lenient:
            raise SubtitleError("line 1: byte-order mark is not allowed in strict mode")
        content = content[1:]
        warnings.append("line 1: stripped byte-order mark")

    lines = content.replace("\r\n", "\n").replace("\r", "\n").split("\n")

    blocks: list[tuple[int, list[str]]] = []
    current: list[str] = []
    start_line = 1
    for line_no, line in enumerate(lines, start=1):
        if line.strip() == "":
            if current:
                blocks.append((start_line, current))
                current = []
            continue
        if not current:
            start_line = line_no
        current.append(line)
    if current:
        blocks.append((start_line, current))

    if not blocks and not lenient:
        raise SubtitleError("file contains no subtitle blocks")

    cues: list[Cue] = []
    expected_index = 1
    prev_start = -1

    for start_line, block_lines in blocks:
        if len(block_lines) < 3:
            message = f"line {start_line}: block has fewer than 3 lines"
            if not lenient:
                raise SubtitleError(message)
            warnings.append(message + ", skipped")
            continue

        index_line = block_lines[0].strip()
        if index_line.lstrip("-").isdigit():
            index = int(index_line)
            if index != expected_index:
                message = f"line {start_line}: expected index {expected_index}, got {index}"
                if not lenient:
                    raise SubtitleError(message)
                warnings.append(message)
        else:
            message = f"line {start_line}: index {index_line!r} is not an integer"
            if not lenient:
                raise SubtitleError(message)
            warnings.append(message + f", treated as {expected_index}")
            index = expected_index

        timing_line = block_lines[1].strip()
        parts = timing_line.split("-->")
        if len(parts) != 2:
            message = f"line {start_line + 1}: malformed timing line {timing_line!r}"
            if not lenient:
                raise SubtitleError(message)
            warnings.append(message + ", block skipped")
            expected_index = index + 1
            continue

        start_ms = _parse_timecode(parts[0], lenient, start_line + 1)
        end_ms = _parse_timecode(parts[1], lenient, start_line + 1)

        if end_ms <= start_ms:
            message = f"line {start_line + 1}: end time is not after start time"
            if not lenient:
                raise SubtitleError(message)
            warnings.append(message + ", adjusted")
            start_ms, end_ms = min(start_ms, end_ms), max(start_ms, end_ms)
            if end_ms == start_ms:
                end_ms = start_ms + 1

        if start_ms < prev_start:
            message = f"line {start_line + 1}: start time goes backwards relative to previous cue"
            if not lenient:
                raise SubtitleError(message)
            warnings.append(message)

        text = "\n".join(block_lines[2:]).strip()
        if not text:
            message = f"line {start_line}: cue has no text"
            if not lenient:
                raise SubtitleError(message)
            warnings.append(message)

        cues.append(Cue(index=index, start_ms=start_ms, end_ms=end_ms, text=text, line=start_line))
        prev_start = start_ms
        expected_index = index + 1

    return cues, warnings
