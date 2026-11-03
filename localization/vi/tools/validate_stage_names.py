#!/usr/bin/env python3
"""Check full Vietnamese area-name drafts against the PS1 US source table.

The game stores area labels as two separately rendered pieces. Do not split
Vietnamese phrases automatically or inject them before layout testing.
"""
from __future__ import annotations

import argparse
import csv
import json
import unicodedata
from collections import Counter, defaultdict
from pathlib import Path

try:
    from .source_catalog import catalog
except ImportError:
    from source_catalog import catalog

INPUT = "localization/vi/stage_names_draft.csv"
FIELDS = {"index", "source_part1", "source_part2", "vi_full", "status", "notes"}
VALID = {"draft", "reviewed", "tested_in_game"}


def validate(root: Path) -> dict:
    source = defaultdict(dict)
    for item in catalog(root):
        if item["category"] == "stage":
            source[item["index"]][item["field"]] = item["original"]
    issues = []
    seen = set()
    counts = Counter()
    with (root / INPUT).open(encoding="utf-8-sig", newline="") as stream:
        reader = csv.DictReader(stream)
        if reader.fieldnames is None or set(reader.fieldnames) != FIELDS:
            raise ValueError(f"Incorrect area-name draft columns: {reader.fieldnames}")
        rows = list(reader)

    for line_no, row in enumerate(rows, 2):
        try:
            index = int(row["index"])
        except ValueError:
            issues.append(f"line {line_no}: invalid integer index")
            continue
        if index in seen:
            issues.append(f"line {line_no}: duplicate area index {index}")
        seen.add(index)
        expected = source.get(index)
        if expected is None:
            issues.append(f"line {line_no}: unknown or empty area index {index}")
            continue
        for field, original in (("part1", "source_part1"), ("part2", "source_part2")):
            if row[original] != expected.get(field, ""):
                issues.append(f"line {line_no}: stale {field} source for area {index}")
        vi = row["vi_full"]
        if not vi.strip():
            issues.append(f"line {line_no}: empty Vietnamese area {index}")
        if unicodedata.normalize("NFC", vi) != vi:
            issues.append(f"line {line_no}: non-NFC Vietnamese for area {index}")
        if row["status"] not in VALID:
            issues.append(f"line {line_no}: invalid status for area {index}")
        else:
            counts[row["status"]] += 1

    missing = sorted(set(source) - seen)
    if missing:
        issues.append(f"Missing US area indices: {missing}")
    return {
        "area_names_in_source": len(source),
        "area_names_drafted": len(rows),
        "states": dict(counts),
        "issues": issues,
        "layout_verified": False,
        "warning": "Each source area uses two strings. Full Vietnamese wording has not been laid out into game lines.",
    }


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--repo-root", type=Path, default=Path(__file__).resolve().parents[3])
    args = parser.parse_args()
    try:
        result = validate(args.repo_root)
    except (OSError, ValueError, csv.Error) as exc:
        print(json.dumps({"error": str(exc)}, ensure_ascii=False))
        return 2
    print(json.dumps(result, indent=2, ensure_ascii=False))
    return 1 if result["issues"] else 0


if __name__ == "__main__":
    raise SystemExit(main())
