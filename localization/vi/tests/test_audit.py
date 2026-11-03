"""Offline regression tests for the Vietnamese source/encoding audit."""
import csv
import sys
import tempfile
import unittest
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from tools.audit import AuditError, audit, extract_psx_font, extract_us_menu  # noqa: E402

MENU = '''const char* D_800A2D48[] = {
#if defined(VERSION_US)
    "？？？？？",
    "Button set−up",
    "Sound settings",
#elif defined(VERSION_HD)
    "日本語",
#endif
};
'''
FONT = (
    'var psxFontTable = []rune(strings.Join([]string{\n'
    + chr(96) + "A" * 256 + chr(96) + '\n}, ""))'
)
COLUMNS = ["source_file", "source_symbol", "platform", "original", "vi", "status", "notes"]


class AuditTests(unittest.TestCase):
    def make_repo(self, root, rows):
        root = Path(root)
        for directory in ("src/dra", "tools/sotn-assets/sotn", "localization/vi"):
            (root / directory).mkdir(parents=True, exist_ok=True)
        (root / "src/dra/menu.c").write_text(MENU, encoding="utf-8")
        (root / "tools/sotn-assets/sotn/string.go").write_text(FONT, encoding="utf-8")
        with (root / "localization/vi/menu_draft.csv").open(
            "w", encoding="utf-8", newline=""
        ) as stream:
            writer = csv.DictWriter(stream, fieldnames=COLUMNS)
            writer.writeheader()
            writer.writerows(rows)
        return root

    @staticmethod
    def row(original="Button set−up", translated="Cài đặt nút"):
        return {
            "source_file": "src/dra/menu.c",
            "source_symbol": "D_800A2D48[1]",
            "platform": "us",
            "original": original,
            "vi": translated,
            "status": "draft",
            "notes": "",
        }

    def test_extract_us_not_japanese(self):
        self.assertEqual(
            extract_us_menu(MENU),
            ["？？？？？", "Button set−up", "Sound settings"],
        )

    def test_font_table_must_have_256_mapped_characters(self):
        self.assertEqual(extract_psx_font(FONT), {"A"})
        with self.assertRaises(AuditError):
            extract_psx_font(FONT.replace("A" * 256, "A" * 255))

    def test_valid_translation_is_warning_not_successful_build(self):
        with tempfile.TemporaryDirectory() as tmp:
            report = audit(self.make_repo(tmp, [self.row()]))
        self.assertFalse(report["source_issues"])
        self.assertEqual(report["candidate_count"], 1)
        self.assertEqual(report["menu_translatable"], 2)
        self.assertFalse(report["build_verified"])
        self.assertEqual(len(report["font_warnings"]), 1)

    def test_upstream_original_mismatch_is_detected(self):
        with tempfile.TemporaryDirectory() as tmp:
            report = audit(self.make_repo(tmp, [self.row(original="Changed")]))
        self.assertTrue(any("source text changed" in x for x in report["source_issues"]))

    def test_duplicate_key_is_detected(self):
        with tempfile.TemporaryDirectory() as tmp:
            row = self.row()
            report = audit(self.make_repo(tmp, [row, row]))
        self.assertTrue(any("duplicate key" in x for x in report["source_issues"]))

    def test_invalid_status_is_detected(self):
        with tempfile.TemporaryDirectory() as tmp:
            row = self.row()
            row["status"] = "complete"
            report = audit(self.make_repo(tmp, [row]))
        self.assertTrue(any("invalid status" in x for x in report["source_issues"]))


if __name__ == "__main__":
    unittest.main()
