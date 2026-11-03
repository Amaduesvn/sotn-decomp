"""Guard against stale/invalid localization data without any retail game files."""
import csv
import sys
import tempfile
import unittest
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from tools.validate_drafts import inspect  # noqa: E402

MAIN = '''
const char* g_MenuStr[] = {
    _S("LEVEL"),
};
SpellDef g_SpellDefs[] = {
    {"Hellfire", _S("↑↓→"), "Fireball attack", 15, 20},
};
RelicDesc g_RelicDefs[] = {
    {"Soul of Bat", "Transform into Bat", 256, 256, 0},
};
'''
SELECT = '''
StageName D_80180128[80] = {
    {_S("Marble"), _S("Gallery")},
};
'''
FIELDS = ["key", "original", "vi", "status", "notes"]


def write_fixture(root: Path, records: list[dict]) -> None:
    paths = {
        "src/config_us.h": MAIN,
        "src/st/sel/2C048.c": SELECT,
        "tools/sotn-assets/sotn/string.go": (
            'var psxFontTable = []rune(strings.Join([]string{\n'
            + chr(96) + "A" * 256 + chr(96) + '\n}, ""))'
        ),
    }
    for name, text in paths.items():
        file = root / name
        file.parent.mkdir(parents=True, exist_ok=True)
        file.write_text(text, encoding="utf-8")
    file = root / "localization/vi/us_translation_draft.csv"
    file.parent.mkdir(parents=True, exist_ok=True)
    with file.open("w", encoding="utf-8", newline="") as stream:
        writer = csv.DictWriter(stream, fieldnames=FIELDS)
        writer.writeheader()
        writer.writerows(records)


def row(key="g_MenuStr[0].text", original="LEVEL", vi="Cấp độ", status="draft"):
    return {"key": key, "original": original, "vi": vi, "status": status, "notes": ""}


class DraftValidationTests(unittest.TestCase):
    def run_fixture(self, data):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            write_fixture(root, data)
            return inspect(root)

    def test_valid_draft_warns_about_missing_font_only(self):
        result = self.run_fixture([row()])
        self.assertEqual(result["draft_entries"], 1)
        self.assertFalse(result["source_issues"])
        self.assertEqual(result["status_counts"], {"draft": 1})
        self.assertFalse(result["tested_in_emulator"])
        self.assertGreater(result["warning_count"], 0)

    def test_invalid_or_unknown_reference(self):
        report = self.run_fixture([row(key="g_MenuStr[55].text")])
        self.assertTrue(any("unknown key" in x for x in report["source_issues"]))

    def test_stale_original(self):
        report = self.run_fixture([row(original="NEW LEVEL")])
        self.assertTrue(any("stale original" in x for x in report["source_issues"]))

    def test_duplicate_keys(self):
        report = self.run_fixture([row(), row()])
        self.assertTrue(any("duplicate key" in x for x in report["source_issues"]))

    def test_non_nfc_combining_marks(self):
        report = self.run_fixture([row(vi="Ca\u0301p")])
        self.assertTrue(any("not normalized" in x for x in report["source_issues"]))

    def test_bad_status(self):
        report = self.run_fixture([row(status="done")])
        self.assertTrue(any("invalid status" in x for x in report["source_issues"]))


if __name__ == "__main__":
    unittest.main()
