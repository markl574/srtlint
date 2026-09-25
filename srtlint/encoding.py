"""Best-effort diagnosis of non-UTF-8 subtitle files.

SRT has no encoding declaration, so tools disagree: some editors save
UTF-16, others save whatever the OS's legacy codepage was (Windows-1252
in practice, for files coming out of Western European tooling). When
UTF-8 decoding fails we want to tell the user what they're actually
looking at instead of just "not valid utf-8", since "re-save as UTF-8"
is only actionable if they know what it currently is.
"""

from __future__ import annotations


def sniff_encoding(raw: bytes) -> str | None:
    """Guess the encoding of bytes that are known not to be UTF-8.

    Returns a codec name suitable for str.encode()/decode(), or None if
    nothing matched confidently enough to be worth reporting.
    """
    if raw.startswith(b"\x00\x00\xfe\xff"):
        return "utf-32-be"
    if raw.startswith(b"\xff\xfe\x00\x00"):
        return "utf-32-le"
    if raw.startswith(b"\xfe\xff"):
        return "utf-16-be"
    if raw.startswith(b"\xff\xfe"):
        return "utf-16-le"

    # No BOM. SRT is mostly ASCII digits and punctuation in the index and
    # timing lines, so unmarked UTF-16 text shows up as a null byte in
    # every other position — the null falls on the high byte of a
    # UTF-16LE code unit, or the low byte of a UTF-16BE one.
    if len(raw) >= 4 and raw.count(b"\x00") > len(raw) // 4:
        if raw[1::2].count(0) > raw[0::2].count(0):
            return "utf-16-le"
        if raw[0::2].count(0) > raw[1::2].count(0):
            return "utf-16-be"

    try:
        raw.decode("ascii")
    except UnicodeDecodeError:
        try:
            raw.decode("cp1252")
        except UnicodeDecodeError:
            pass
        else:
            return "windows-1252"

    return None
