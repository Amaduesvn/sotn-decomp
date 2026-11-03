#!/usr/bin/env python3
"""Extract stable, editable PS1 US text references from checked-in C sources.

Works offline and does not require a game image. This is a SOURCE inventory,
not a patch builder. Never edit game engine strings by substituting UTF-8.
"""
from __future__ import annotations

import argparse
import ast
import csv
import io
import json
import re
from collections import Counter
from pathlib import Path

CONFIG = "src/config_us.h"
SELECT = "src/st/sel/2C048.c"
FIELDS = ("key", "source_file", "category", "symbol", "index", "field", "original")

# C string literal subset used in the selected source arrays.
Q = r'"(?:\\.|[^"\\])*"'


class CatalogError(ValueError):
    pass


def decode_literal(token: str) -> str:
    try:
        result = ast.literal_eval(token)
    except (ValueError, SyntaxError) as exc:
        raise CatalogError(f"Malformed C string: {token}") from exc
    if not isinstance(result, str):
        raise CatalogError(f"Not a quoted string: {token}")
    return result


def array_lines(source: str, symbol: str) -> list[str]:
    pattern = r"\b" + re.escape(symbol) + r"\s*\[[^\]]*\]\s*=\s*\{(.*?)\n\};"
    found = re.search(pattern, source, re.DOTALL)
    if not found:
        raise CatalogError(f"Cannot locate array {symbol}")
    return [
        x.strip() for x in found.group(1).splitlines()
        if x.strip() and not x.strip().startswith("//")
    ]


def extract_array(source: str, source_file: str, symbol: str, category: str) -> list[dict]:
    lines = array_lines(source, symbol)
    rows: list[dict] = []
    if category == "menu":
        pattern = re.compile(r"^_S\(\s*(" + Q + r")\s*\)\s*,?\s*$")
        fields = ("text",)
    elif category == "spell":
        pattern = re.compile(
            r"^\{\s*(" + Q + r")\s*,\s*_S\(\s*" + Q
            + r"\s*\)\s*,\s*(" + Q + r")\s*,.*\},?\s*$"
        )
        fields = ("name", "description")
    elif category == "relic":
        pattern = re.compile(r"^\{\s*(" + Q + r")\s*,\s*(" + Q + r")\s*,.*\},?\s*$")
        fields = ("name", "description")
    elif category == "stage":
        pattern = re.compile(
            r"^\{\s*_S\(\s*(" + Q + r")\s*\)\s*,\s*_S\(\s*(" + Q
            + r")\s*\)\s*\}\s*,?\s*$"
        )
        fields = ("part1", "part2")
    else:
        raise CatalogError(f"Unsupported category: {category}")

    for index, line in enumerate(lines):
        match = pattern.fullmatch(line)
        if not match:
            raise CatalogError(f"{source_file} {symbol}[{index}]: unknown syntax: {line}")
        values = [decode_literal(x) for x in match.groups()]
        for field, value in zip(fields, values):
            # Preserve original array index even if the slot is empty.
            if not value:
                continue
            rows.append({
                "key": f"{symbol}[{index}].{field}",
                "source_file": source_file,
                "category": category,
                "symbol": symbol,
                "index": index,
                "field": field,
                "original": value,
            })
    return rows


def catalog(root: Path) -> list[dict]:
    main = (root / CONFIG).read_text(encoding="utf-8")
    select = (root / SELECT).read_text(encoding="utf-8")
    rows = []
    for spec in (
        (main, CONFIG, "g_MenuStr", "menu"),
        (main, CONFIG, "g_SpellDefs", "spell"),
        (main, CONFIG, "g_RelicDefs", "relic"),
        (select, SELECT, "D_80180128", "stage"),
    ):
        rows.extend(extract_array(*spec))
    if len({x["key"] for x in rows}) != len(rows):
        raise CatalogError("Duplicate catalog key; source arrays are ambiguous")
    return rows


def serialize(rows: list[dict]) -> str:
    out = io.StringIO(newline="")
    writer = csv.DictWriter(out, fieldnames=FIELDS, lineterminator="\n")
    writer.writeheader()
    writer.writerows(rows)
    return out.getvalue()


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--repo-root", type=Path, default=Path(__file__).resolve().parents[3])
    parser.add_argument("--write", type=Path, help="Write a reproducible source snapshot CSV")
    parser.add_argument("--check", type=Path, help="Fail if a checked-in source snapshot is stale")
    args = parser.parse_args()
    try:
        rows = catalog(args.repo_root)
        text = serialize(rows)
        if args.write:
            args.write.parent.mkdir(parents=True, exist_ok=True)
            args.write.write_text(text, encoding="utf-8", newline="")
        if args.check and args.check.read_text(encoding="utf-8") != text:
            print(json.dumps({"error": f"Stale source snapshot: {args.check}"}))
            return 1
    except (CatalogError, OSError) as exc:
        print(json.dumps({"error": str(exc)}, ensure_ascii=False))
        return 2
    print(json.dumps({
        "entries": len(rows),
        "by_category": dict(Counter(x["category"] for x in rows)),
        "source_files": [CONFIG, SELECT],
        "notes": "Original C string inventory, not a game build or Vietnamese coverage count",
    }, ensure_ascii=False, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
