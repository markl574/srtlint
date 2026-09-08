"""Command-line entry point for srtlint."""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

from .parser import SubtitleError, parse


def _check_file(path: Path, lenient: bool) -> dict:
    result = {"path": str(path), "ok": False, "cues": 0, "warnings": [], "error": None}

    try:
        content = path.read_text(encoding="utf-8")
    except OSError as exc:
        result["error"] = str(exc)
        return result
    except UnicodeDecodeError as exc:
        result["error"] = f"not valid utf-8 ({exc})"
        return result

    try:
        cues, warnings = parse(content, lenient=lenient)
    except SubtitleError as exc:
        result["error"] = str(exc)
        return result

    result["ok"] = True
    result["cues"] = len(cues)
    result["warnings"] = warnings
    return result


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
    ap.add_argument(
        "--format",
        choices=("text", "json"),
        default="text",
        help="output format: human-readable text (default) or a single JSON "
        "array of per-file results, for consumption by CI",
    )
    args = ap.parse_args(argv)

    results = [_check_file(path, args.lenient) for path in args.files]
    had_errors = any(r["error"] is not None for r in results)

    if args.format == "json":
        print(json.dumps(results, indent=2))
        return 1 if had_errors else 0

    for result in results:
        path = result["path"]
        if result["error"] is not None:
            print(f"{path}: {result['error']}", file=sys.stderr)
            continue
        for warning in result["warnings"]:
            print(f"{path}: warning: {warning}")
        print(f"{path}: ok ({result['cues']} cues)")

    return 1 if had_errors else 0


def run() -> None:
    sys.exit(main())


if __name__ == "__main__":
    run()
