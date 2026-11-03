#!/usr/bin/env python3
"""Prepare safe, source-keyed cutscene translation drafts from extracted YAML.

This tool does NOT read retail game discs, encode PS1 Vietnamese glyphs, or
produce a playable patch. UTF-8 staging YAML is not safe to feed into the
current cutscene Go builder without the required encoding/renderer changes.
"""
from __future__ import annotations

import argparse
import ast
import csv
import io
import json
import re
from pathlib import Path

PATTERN = re.compile(
    r'^(?P<prefix>\s*-\s*\[\s*TEXT\s*,\s*)"'
    r'(?P<body>(?:\\.|[^"\\])*)"'
    r'(?P<suffix>\s*\]\s*(?:#.*)?)$'
)
FIELDS = ("script", "text_index", "original", "vi", "status", "notes")
VALID_STATES = {"draft", "reviewed"}


class ScriptError(ValueError):
    pass


def parse_text_lines(script: str) -> list[dict]:
    result = []
    for line_no, line in enumerate(script.splitlines(), 1):
        match = PATTERN.match(line)
        if not match:
            if re.match(r"^\s*-\s*\[\s*TEXT\s*,", line):
                raise ScriptError(f"Unsupported TEXT syntax on line {line_no}")
            continue
        try:
            raw = '"' + match.group("body") + '"'
            original = ast.literal_eval(raw)
        except (ValueError, SyntaxError) as exc:
            raise ScriptError(f"Invalid escaped TEXT on line {line_no}") from exc
        result.append({"text_index": len(result), "line_number": line_no,
                       "original": original})
    return result


def extract_csv(script: str, script_id: str) -> str:
    if not script_id.strip():
        raise ScriptError("Script ID cannot be empty")
    out = io.StringIO(newline="")
    writer = csv.DictWriter(out, fieldnames=FIELDS, lineterminator="\n")
    writer.writeheader()
    for row in parse_text_lines(script):
        writer.writerow({
            "script": script_id, "text_index": row["text_index"],
            "original": row["original"], "vi": "", "status": "draft",
            "notes": "Giữ nguyên sự kiện và lệnh điều khiển; chưa có font PS1",
        })
    return out.getvalue()


def stage_yaml(script: str, script_id: str, translated_csv: str) -> tuple[str, dict]:
    original = parse_text_lines(script)
    reader = csv.DictReader(io.StringIO(translated_csv))
    if reader.fieldnames is None or set(reader.fieldnames) != set(FIELDS):
        raise ScriptError("Unexpected cutscene translation CSV columns")
    rows = list(reader)
    seen: set[int] = set()
    replacements: dict[int, str] = {}
    for csv_line, row in enumerate(rows, 2):
        if row["script"] != script_id:
            raise ScriptError(f"CSV line {csv_line}: script mismatch")
        try:
            idx = int(row["text_index"])
        except ValueError as exc:
            raise ScriptError(f"CSV line {csv_line}: invalid text_index") from exc
        if idx < 0 or idx >= len(original) or idx in seen:
            raise ScriptError(f"CSV line {csv_line}: unknown/duplicate index {idx}")
        seen.add(idx)
        if original[idx]["original"] != row["original"]:
            raise ScriptError(f"CSV line {csv_line}: stale original at index {idx}")
        if row["status"] not in VALID_STATES:
            raise ScriptError(f"CSV line {csv_line}: invalid status {row['status']}")
        value = row["vi"]
        if value and ("\n" in value or "\r" in value or "\x00" in value):
            raise ScriptError(f"CSV line {csv_line}: unsupported line/control char")
        if value:
            replacements[idx] = value
    if len(seen) != len(original):
        raise ScriptError("Translation CSV is incomplete for this script")

    lines = script.splitlines(keepends=True)
    idx = 0
    for n, line in enumerate(lines):
        body = line.rstrip("\r\n")
        suffix = line[len(body):]
        match = PATTERN.match(body)
        if match is None:
            continue
        if idx in replacements:
            # Produces YAML-compatible quoted UTF-8 strings. These are STAGING
            # translations only, not encoded bytes for the PS1 cutscene engine.
            quoted = json.dumps(replacements[idx], ensure_ascii=False)
            lines[n] = match.group("prefix") + quoted + match.group("suffix") + suffix
        idx += 1
    return "".join(lines), {
        "script": script_id, "total_text_entries": len(original),
        "staged_text_entries": len(replacements),
        "script_control_rows_untouched": True,
        "ps1_encoding_verified": False, "playable_patch": False,
    }


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--script", type=Path, required=True, help="Extracted cutscene YAML")
    parser.add_argument("--script-id", required=True, help="Stable script asset identifier")
    parser.add_argument("--extract-csv", type=Path, help="Generate a blank translation template")
    parser.add_argument("--translations", type=Path, help="Input filled translation CSV")
    parser.add_argument("--staging-yaml", type=Path, help="Write translated YAML as staging text")
    args = parser.parse_args()
    try:
        data = args.script.read_text(encoding="utf-8")
        if args.extract_csv and not args.translations and not args.staging_yaml:
            args.extract_csv.write_text(extract_csv(data, args.script_id), encoding="utf-8")
            print(json.dumps({"extracted_text_entries": len(parse_text_lines(data)),
                              "output": str(args.extract_csv)}, ensure_ascii=False))
            return 0
        if args.translations and args.staging_yaml and not args.extract_csv:
            staged, report = stage_yaml(
                data, args.script_id, args.translations.read_text(encoding="utf-8-sig")
            )
            args.staging_yaml.write_text(staged, encoding="utf-8")
            print(json.dumps(report, ensure_ascii=False, indent=2))
            return 0
        raise ScriptError("Use either --extract-csv OR --translations + --staging-yaml")
    except (OSError, ValueError, csv.Error) as exc:
        print(json.dumps({"error": str(exc)}, ensure_ascii=False))
        return 2


if __name__ == "__main__":
    raise SystemExit(main())
