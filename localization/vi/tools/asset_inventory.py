#!/usr/bin/env python3
"""Inventory US game-text asset declarations, without reading proprietary files.

The result lists locations to investigate, not translated strings or coverage.
"""
from __future__ import annotations

import argparse
import json
import re
from collections import Counter
from pathlib import Path

CONFIG = "config/assets.us.yaml"
ASSET_LINE = re.compile(
    r"^\s*-\s*\[\s*(0x[0-9a-fA-F]+)\s*,\s*([a-z_]+)\s*,\s*([^,\]]+)"
)
TARGET_LINE = re.compile(r"^\s*-\s*target:\s*([^\s#]+)")
DATA_TYPES = {"equipment", "accessories", "enemydefs", "cutscene", "credits"}


def inventory(config: str) -> dict:
    target = None
    sources = []
    for line_no, line in enumerate(config.splitlines(), 1):
        line = line.split("#", 1)[0].rstrip()
        match = TARGET_LINE.match(line)
        if match:
            target = match.group(1)
            continue
        match = ASSET_LINE.match(line)
        if match is None:
            continue
        offset, asset_type, name = match.groups()
        name = name.strip()
        kind = asset_type
        if kind == "cmpgfx" and "stage_name_en" in name:
            kind = "stage_name_graphic"
        if kind not in DATA_TYPES and kind != "stage_name_graphic":
            continue
        sources.append({
            "kind": kind,
            "target": target,
            "asset_name": name,
            "offset": offset,
            "config_line": line_no,
        })
    summary = dict(sorted(Counter(row["kind"] for row in sources).items()))
    return {
        "reference": "PS1 US SLUS-00067",
        "config": CONFIG,
        "declared_asset_count": len(sources),
        "declared_assets_by_type": summary,
        "sources": sources,
        "limitation": (
            "These are asset declarations, not string counts. Actual game files "
            "are required for extraction; some text lives in C source instead."
        ),
    }


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--repo-root", type=Path, default=Path(__file__).resolve().parents[3])
    parser.add_argument("--summary", action="store_true", help="Omit individual source records")
    args = parser.parse_args()
    path = args.repo_root / CONFIG
    try:
        report = inventory(path.read_text(encoding="utf-8"))
    except OSError as exc:
        print(json.dumps({"error": str(exc)}))
        return 1
    if args.summary:
        report.pop("sources")
    print(json.dumps(report, indent=2, ensure_ascii=False))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
