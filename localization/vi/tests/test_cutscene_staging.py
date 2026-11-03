"""Protect cutscene event/control bytes when preparing Vietnamese drafts."""
import csv
import io
import sys
import unittest
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from tools.cutscene_staging import (  # noqa: E402
    ScriptError, extract_csv, parse_text_lines, stage_yaml,
)

EXAMPLE = (
    "script:\n"
    "  - [SET_SPEED, 3]\n"
    '  - [TEXT, "Hello"]\n'
    "  - [LINE_BREAK]\n"
    "  - [PLAY_SOUND, 0x0300]\n"
    '  - [TEXT, "Goodbye"]\n'
    "  - [END_CUTSCENE]\n"
)


def draft(*names):
    source = extract_csv(EXAMPLE, "stage/test_cutscene")
    data = list(csv.DictReader(io.StringIO(source)))
    for row, name in zip(data, names):
        row["vi"] = name
        row["status"] = "reviewed"
    out = io.StringIO(newline="")
    writer = csv.DictWriter(out, fieldnames=list(data[0]), lineterminator="\n")
    writer.writeheader()
    writer.writerows(data)
    return out.getvalue()


class CutsceneTests(unittest.TestCase):
    def test_extract_preserves_script_order(self):
        data = parse_text_lines(EXAMPLE)
        self.assertEqual([(r["text_index"], r["original"]) for r in data],
                         [(0, "Hello"), (1, "Goodbye")])

    def test_stage_replaces_only_text_controls_unchanged(self):
        staged, report = stage_yaml(
            EXAMPLE, "stage/test_cutscene", draft("Xin chào", "Tạm biệt")
        )
        self.assertIn('  - [TEXT, "Xin chào"]\n', staged)
        self.assertIn("  - [LINE_BREAK]\n", staged)
        self.assertIn("  - [PLAY_SOUND, 0x0300]\n", staged)
        self.assertIn("  - [SET_SPEED, 3]\n", staged)
        self.assertIn("  - [END_CUTSCENE]\n", staged)
        self.assertEqual(report["staged_text_entries"], 2)
        self.assertFalse(report["ps1_encoding_verified"])
        self.assertFalse(report["playable_patch"])

    def test_stale_original_rejected(self):
        csv_text = draft("Xin chào", "Tạm biệt").replace("Hello", "Changed")
        with self.assertRaisesRegex(ScriptError, "stale original"):
            stage_yaml(EXAMPLE, "stage/test_cutscene", csv_text)

    def test_duplicate_indices_rejected(self):
        data = list(csv.DictReader(io.StringIO(draft("A", "B"))))
        data[1]["text_index"] = 0
        out = io.StringIO(newline="")
        writer = csv.DictWriter(out, fieldnames=list(data[0]))
        writer.writeheader()
        writer.writerows(data)
        with self.assertRaisesRegex(ScriptError, "duplicate"):
            stage_yaml(EXAMPLE, "stage/test_cutscene", out.getvalue())

    def test_unsupported_text_row_rejected(self):
        invalid = 'script:\n  - [TEXT, not_quoted]\n'
        with self.assertRaisesRegex(ScriptError, "Unsupported TEXT"):
            parse_text_lines(invalid)

    def test_quote_is_escaped_in_staging(self):
        staged, _ = stage_yaml(
            EXAMPLE, "stage/test_cutscene", draft('Nói "Xin chào"', "Tạm biệt")
        )
        self.assertIn('Nói \\"Xin chào\\"', staged)


if __name__ == "__main__":
    unittest.main()
