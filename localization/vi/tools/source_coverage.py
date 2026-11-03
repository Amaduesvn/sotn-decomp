#!/usr/bin/env python3
"""Account for all currently known PS1 US source strings before BIN extraction.

This is *source accounting*, not game localization progress. All current
Vietnamese translations remain unbuilt and untested in the PS1 engine.
"""
from __future__ import annotations

import argparse
import csv
import json
from collections import Counter
from pathlib import Path

try:
    from .source_catalog import catalog
    from .validate_drafts import inspect as validate_drafts
    from .validate_stage_names import validate as validate_stages
except ImportError:
    from source_catalog import catalog
    from validate_drafts import inspect as validate_drafts
    from validate_stage_names import validate as validate_stages

DRAFTS = "localization/vi/us_translation_draft.csv"
EXCLUSIONS = "localization/vi/menu_preserve_defer.csv"
AREA = "localization/vi/stage_names_draft.csv"


def read_csv(path: Path) -> list[dict]:
    with path.open(encoding="utf-8-sig", newline="") as stream:
        return list(csv.DictReader(stream))


def inspect(root: Path) -> dict:
    catalog_rows = catalog(root)
    known = {x["key"]: x for x in catalog_rows}
    draft_check = validate_drafts(root)
    stage_check = validate_stages(root)
    translated = read_csv(root / DRAFTS)
    exclusions = read_csv(root / EXCLUSIONS)
    area_names = read_csv(root / AREA)

    problems = draft_check["source_issues"] + stage_check["issues"]
    classified: dict[str, str] = {}
    for row in translated:
        classified[row["key"]] = "draft"
    decisions = Counter()
    for row in exclusions:
        key = row["key"]
        if key in classified:
            problems.append(f"Translation and exclusion conflict: {key}")
        classified[key] = row["decision"]
        src = known.get(key)
        if src is None or src["category"] != "menu":
            problems.append(f"Unknown/non-menu exclusion key: {key}")
        elif row["original"] != src["original"]:
            problems.append(f"Stale exclusion original: {key}")
        if row["decision"] not in {"preserve", "defer"}:
            problems.append(f"Invalid exclusion decision: {key}")
        else:
            decisions[row["decision"]] += 1

    for row in area_names:
        try:
            index = int(row["index"])
        except ValueError:
            problems.append(f"Non-numeric stage index: {row['index']}")
            continue
        for field in ("part1", "part2"):
            key = f"D_80180128[{index}].{field}"
            if key in known:
                if key in classified:
                    problems.append(f"Conflicting classification: {key}")
                classified[key] = "full_area_name_draft"

    unknown = sorted(set(classified) - set(known))
    if unknown:
        problems.append(f"Unknown source keys: {unknown}")

    missing = sorted(set(known) - set(classified))
    if missing:
        problems.append(f"Unclassified US source keys: {missing}")

    categories = Counter()
    for key, classification in classified.items():
        if key in known:
            categories[(known[key]["category"], classification)] += 1
    return {
        "known_source_entries": len(catalog_rows),
        "known_source_entries_accounted": len(set(known) & set(classified)),
        "us_draft_translations": len(translated),
        "full_area_name_drafts": len(area_names),
        "preserved_or_deferred_menu_entries": dict(decisions),
        "breakdown": {
            f"{category}:{state}": n
            for (category, state), n in sorted(categories.items())
        },
        "issues": problems,
        "warning": (
            "100% accounting of these checked-in source strings is not 100% of "
            "the game. Equipment/enemy databases, extracted dialogues, fonts, "
            "graphics and actual in-game verification still require original assets."
        ),
        "in_game_localization_verified": False,
    }


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--repo-root", type=Path, default=Path(__file__).resolve().parents[3])
    args = parser.parse_args()
    try:
        result = inspect(args.repo_root)
    except (ValueError, OSError, csv.Error) as exc:
        print(json.dumps({"error": str(exc)}, ensure_ascii=False))
        return 2
    print(json.dumps(result, ensure_ascii=False, indent=2))
    return 1 if result["issues"] else 0


if __name__ == "__main__":
    raise SystemExit(main())
