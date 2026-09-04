"""Command-line entry point for srtlint."""

from __future__ import annotations

import argparse
import sys
from pathlib import Path

from .parser import SubtitleError, parse


def main(argv: list[str] | None = None) -> int:
    ap = argparse.ArgumentParser(
        prog="srtlint",
        description="Check SRT subtitle files for structural problems.",
    )
    ap.add_argument("files", nargs="+", type=Path, help="SRT files to check")
    ap.add_argument(
        "--lenient",
        action="store_true",
        help="warn instead of failing on recoverable issues (bad index order, "
        "loose timecode formatting, out-of-order cues, empty text, ...)",
    )
    args = ap.parse_args(argv)

    had_errors = False

    for path in args.files:
        try:
            content = path.read_text(encoding="utf-8")
        except OSError as exc:
            print(f"{path}: {exc}", file=sys.stderr)
            had_errors = True
            continue
        except UnicodeDecodeError as exc:
            print(f"{path}: not valid utf-8 ({exc})", file=sys.stderr)
            had_errors = True
            continue

        try:
            cues, warnings = parse(content, lenient=args.lenient)
        except SubtitleError as exc:
            print(f"{path}: {exc}", file=sys.stderr)
            had_errors = True
            continue

        for warning in warnings:
            print(f"{path}: warning: {warning}")

        print(f"{path}: ok ({len(cues)} cues)")

    return 1 if had_errors else 0


def run() -> None:
    sys.exit(main())


if __name__ == "__main__":
    run()
