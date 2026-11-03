#!/usr/bin/env python3
"""Validate editable Vietnamese drafts against immutable US source references.

This is a source-data QA tool. A passing validation DOES NOT mean that the
draft can be encoded, linked into the game or rendered on actual PS1 hardware.
"""
from __future__ import annotations

import argparse
import csv
import json
import unicodedata
from collections import Counter
from pathlib import Path

try:
    from .audit import GO_FONT_SOURCE, extract_psx_font
    from .source_catalog import catalog
except ImportError:
    from audit import GO_FONT_SOURCE, extract_psx_font
    from source_catalog import catalog

TRANSLATIONS = "localization/vi/us_translation_draft.csv"
STATES = {"draft", "reviewed", "tested_in_game"}
FIELDS = {"key", "original", "vi", "status", "notes"}


def inspect(root: Path) -> dict:
    src = catalog(root)
    sources = {r["key"]: r for r in src}
    table = extract_psx_font((root / GO_FONT_SOURCE).read_text(encoding="utf-8"))
    issues = []
    warnings = []
    counts = Counter()
    with (root / TRANSLATIONS).open(encoding="utf-8-sig", newline="") as stream:
        reader = csv.DictReader(stream)
        if reader.fieldnames is None or set(reader.fieldnames) != FIELDS:
            raise ValueError(f"Unexpected translation CSV columns: {reader.fieldnames}")
        rows = list(reader)

    seen = set()
    for line_no, row in enumerate(rows, 2):
        key = row["key"]
        if key in seen:
            issues.append(f"line {line_no}: duplicate key: {key}")
        seen.add(key)
        source = sources.get(key)
        if source is None:
            issues.append(f"line {line_no}: unknown key: {key}")
            continue
        counts[source["category"]] += 1
        if source["original"] != row["original"]:
            issues.append(f"line {line_no}: stale original for {key}")
        if row["status"] not in STATES:
            issues.append(f"line {line_no}: invalid status for {key}")
        if not row["vi"].strip():
            issues.append(f"line {line_no}: empty translation for {key}")
        if unicodedata.normalize("NFC", row["vi"]) != row["vi"]:
            issues.append(f"line {line_no}: Vietnamese text not normalized to NFC for {key}")
        if "\n" in row["vi"] or "\r" in row["vi"] or "\x00" in row["vi"]:
            issues.append(f"line {line_no}: unexpected control character for {key}")
        missing = sorted(set(row["vi"]) - table)
        if missing:
            warnings.append({
                "key": key,
                "issue": "missing_original_8x8_font_mapping",
                "characters": "".join(missing),
                "caveat": "Other renderer paths may use a separate font or Shift-JIS.",
            })
        if len(row["vi"]) > len(row["original"]) * 1.4 + 6:
            warnings.append({
                "key": key,
                "issue": "significant_character_length_growth",
                "source_chars": len(row["original"]),
                "draft_chars": len(row["vi"]),
                "caveat": "Not a proven screen overflow.",
            })

    return {
        "source_catalog_entries": len(src),
        "draft_entries": len(rows),
        "draft_by_category": dict(counts),
        "status_counts": dict(Counter(row["status"] for row in rows)),
        "source_issues": issues,
        "warning_count": len(warnings),
        "warning_summary": dict(Counter(x["issue"] for x in warnings)),
        "warnings": warnings,
        "tested_in_emulator": False,
    }


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--repo-root", type=Path, default=Path(__file__).resolve().parents[3])
    parser.add_argument("--summary", action="store_true", help="Omit individual warnings")
    args = parser.parse_args()
    try:
        report = inspect(args.repo_root)
    except (ValueError, OSError, csv.Error) as exc:
        print(json.dumps({"error": str(exc)}, ensure_ascii=False))
        return 2
    if args.summary:
        report.pop("warnings")
    print(json.dumps(report, indent=2, ensure_ascii=False))
    return 1 if report["source_issues"] else 0


if __name__ == "__main__":
    raise SystemExit(main())
