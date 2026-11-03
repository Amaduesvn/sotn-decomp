#!/usr/bin/env python3
"""Report Vietnamese alphabet glyph coverage in the current PS1 8x8 mapping.

This is an encoding feasibility audit only: it does not edit font textures,
reserve character codes, or guarantee that text will display in the game.
"""
from __future__ import annotations

import argparse
import json
import string
import unicodedata
from pathlib import Path

if __package__:
    from .audit import GO_FONT_SOURCE, extract_psx_font
else:
    from audit import GO_FONT_SOURCE, extract_psx_font

VOWELS = "aăâeêioôơuưy"
TONE_MARKS = "\u0300\u0301\u0309\u0303\u0323"


def vietnamese_alphabet() -> set[str]:
    """All single-codepoint letters in modern Vietnamese orthography."""
    result = set(string.ascii_letters + "đĐ")
    for base in VOWELS:
        result.add(base)
        result.add(base.upper())
        for mark in TONE_MARKS:
            composed = unicodedata.normalize("NFC", base + mark)
            if len(composed) != 1:
                raise ValueError(f"Cannot compose {base!r} + {mark!r}")
            result.add(composed)
            result.add(composed.upper())
    return result


def charset_report(repo_root: Path) -> dict:
    table_source = (repo_root / GO_FONT_SOURCE).read_text(encoding="utf-8")
    existing = extract_psx_font(table_source)
    alphabet = vietnamese_alphabet()
    missing = alphabet - existing
    return {
        "target": "PS1 US 8x8 font encoding",
        "existing_mapped_positions": 256,
        "distinct_existing_glyphs": len(existing),
        "vietnamese_alphabet_letters": len(alphabet),
        "already_in_mapping": len(alphabet & existing),
        "missing_from_mapping": len(missing),
        "missing_letters": "".join(sorted(missing)),
        "note": (
            "A 256-position map is not proof that all positions can be reassigned. "
            "In-game glyph images and other rendering paths remain to be tested."
        ),
    }


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--repo-root", type=Path, default=Path(__file__).resolve().parents[3])
    args = parser.parse_args()
    try:
        result = charset_report(args.repo_root)
    except (OSError, ValueError) as exc:
        print(json.dumps({"error": str(exc)}, ensure_ascii=False))
        return 1
    print(json.dumps(result, indent=2, ensure_ascii=False))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
