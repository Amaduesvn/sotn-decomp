#!/usr/bin/env python3
"""Audit Vietnamese PS1 menu drafts against original source and glyph mapping.

No original ROM or extracted game assets needed. Does NOT build or patch the game.
"""
from __future__ import annotations

import argparse
import ast
import csv
import json
import re
from collections import Counter
from pathlib import Path

ALLOWED_STATES = {"draft", "reviewed", "tested_in_game"}
COLUMNS = ("source_file", "source_symbol", "platform", "original", "vi", "status", "notes")
MENU_SOURCE = "src/dra/menu.c"
MENU_SYMBOL = "D_800A2D48"
GO_FONT_SOURCE = "tools/sotn-assets/sotn/string.go"
CSV_SOURCE = "localization/vi/menu_draft.csv"


class AuditError(ValueError):
    pass


def extract_us_menu(source: str) -> list[str]:
    match = re.search(
        r"const\s+char\s*\*\s*D_800A2D48\s*\[\s*\]\s*=\s*\{(.*?)\n\};",
        source, re.DOTALL,
    )
    if not match:
        raise AuditError("Cannot find D_800A2D48 settings menu array")
    block = re.search(
        r"#if\s+defined\(VERSION_US\)(.*?)#elif\s+defined\(VERSION_HD\)",
        match.group(1), re.DOTALL,
    )
    if not block:
        raise AuditError("Cannot isolate VERSION_US settings strings")
    strings = []
    for line in block.group(1).splitlines():
        line = line.strip()
        if not line or line.startswith("//"):
            continue
        found = re.fullmatch(r'("(?:\\.|[^"\\])*")\s*,?', line)
        if found is None:
            raise AuditError(f"Unexpected menu syntax: {line}")
        try:
            strings.append(ast.literal_eval(found.group(1)))
        except (SyntaxError, ValueError) as exc:
            raise AuditError(f"Invalid menu string: {line}") from exc
    return strings


def extract_psx_font(source: str) -> set[str]:
    match = re.search(
        r'var\s+psxFontTable\s*=\s*\[\]rune\(strings\.Join\(\[\]string\{(.*?)\},\s*""\)\)',
        source, re.DOTALL,
    )
    if not match:
        raise AuditError("Cannot locate PS1 8x8 glyph table")
    rows = re.findall(r"\x60([^\x60]*)\x60", match.group(1))
    glyphs = "".join(rows)
    if len(glyphs) != 256:
        raise AuditError(f"Expected 256 PS1 glyph mappings, found {len(glyphs)}")
    return set(glyphs)


def audit(repo_root: Path) -> dict:
    menu = extract_us_menu((repo_root / MENU_SOURCE).read_text(encoding="utf-8"))
    glyphs = extract_psx_font((repo_root / GO_FONT_SOURCE).read_text(encoding="utf-8"))
    with (repo_root / CSV_SOURCE).open(newline="", encoding="utf-8-sig") as stream:
        reader = csv.DictReader(stream)
        if reader.fieldnames is None or set(reader.fieldnames) != set(COLUMNS):
            raise AuditError(f"Expected CSV columns: {', '.join(COLUMNS)}")
        rows = list(reader)

    issues = []
    warnings = []
    keys = set()
    states = Counter()
    for line_number, row in enumerate(rows, start=2):
        key = row["source_symbol"]
        if key in keys:
            issues.append(f"Line {line_number}: duplicate key {key}")
        keys.add(key)
        if row["source_file"] != MENU_SOURCE or row["platform"] != "us":
            issues.append(f"Line {line_number}: unsupported source/platform")
        match = re.fullmatch(r"D_800A2D48\[(\d+)\]", key)
        if match is None:
            issues.append(f"Line {line_number}: unknown key {key}")
        else:
            index = int(match.group(1))
            if index >= len(menu):
                issues.append(f"Line {line_number}: index {index} out of range")
            elif row["original"] != menu[index]:
                issues.append(f"Line {line_number}: source text changed for {key}")
        if row["status"] not in ALLOWED_STATES:
            issues.append(f"Line {line_number}: invalid status {row['status']}")
        else:
            states[row["status"]] += 1
        if not row["vi"].strip():
            issues.append(f"Line {line_number}: empty translation")
        if "\n" in row["vi"] or "\r" in row["vi"]:
            issues.append(f"Line {line_number}: line break requires explicit script handling")
        missing = "".join(sorted(set(row["vi"]) - glyphs))
        if missing:
            warnings.append({
                "key": key,
                "unsupported_psx_8x8_glyphs": missing,
                "note": "Font/encoding adaptation needed; not yet a tested game build.",
            })
    translatable = max(0, len(menu) - 1)  # entry zero is the ????? placeholder
    coverage_keys = {f"{MENU_SYMBOL}[{i}]" for i in range(1, len(menu))}
    return {
        "target": "PS1 US SLUS-00067",
        "menu_entries": len(menu),
        "menu_translatable": translatable,
        "candidate_count": len(keys & coverage_keys),
        "states": dict(states),
        "source_issues": issues,
        "font_warnings": warnings,
        "build_verified": False,
    }


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--repo-root", type=Path, default=Path(__file__).resolve().parents[3])
    parser.add_argument("--json", action="store_true", help="Machine-readable report")
    args = parser.parse_args()
    try:
        report = audit(args.repo_root)
    except (AuditError, OSError, csv.Error) as exc:
        print(json.dumps({"error": str(exc)}, ensure_ascii=False))
        return 2
    if args.json:
        print(json.dumps(report, indent=2, ensure_ascii=False))
    else:
        print(f"US settings menu candidates: {report['candidate_count']}/{report['menu_translatable']}")
        print(f"States: {report['states']}")
        for issue in report["source_issues"]:
            print(f"ERROR: {issue}")
        for warning in report["font_warnings"]:
            print(f"FONT: {warning['key']} missing {warning['unsupported_psx_8x8_glyphs']}")
        print("In-game build: NOT TESTED")
    return 1 if report["source_issues"] else 0


if __name__ == "__main__":
    raise SystemExit(main())
