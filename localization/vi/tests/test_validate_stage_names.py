"""Area-name drafts: source pair validation without a game image."""
import csv
import sys
import tempfile
import unittest
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from tools.validate_stage_names import validate  # noqa: E402

MAIN = '''
const char* g_MenuStr[] = {
    _S("ALUCARD"),
};
SpellDef g_SpellDefs[] = {
    {"Hellfire", _S("↑↓→"), "Fireball", 1},
};
RelicDesc g_RelicDefs[] = {
    {"Soul of Bat", "Transform", 1},
};
'''
SELECT = '''
StageName D_80180128[80] = {
    {_S("Marble"), _S("Gallery")},
    {_S("Catacombs"), _S("")},
};
'''
FIELDS = ["index", "source_part1", "source_part2", "vi_full", "status", "notes"]


def fixture(path: Path, records):
    for name, contents in (("src/config_us.h", MAIN), ("src/st/sel/2C048.c", SELECT)):
        source = path / name
        source.parent.mkdir(parents=True, exist_ok=True)
        source.write_text(contents, encoding="utf-8")
    output = path / "localization/vi/stage_names_draft.csv"
    output.parent.mkdir(parents=True, exist_ok=True)
    with output.open("w", encoding="utf-8", newline="") as f:
        writer = csv.DictWriter(f, fieldnames=FIELDS)
        writer.writeheader()
        writer.writerows(records)


def item(index, p1, p2, vi):
    return dict(index=index, source_part1=p1, source_part2=p2, vi_full=vi,
                status="draft", notes="")


class StageValidationTests(unittest.TestCase):
    def check(self, records):
        with tempfile.TemporaryDirectory() as tmp:
            fixture(Path(tmp), records)
            return validate(Path(tmp))

    def test_both_stage_names_match(self):
        result = self.check([item(0, "Marble", "Gallery", "Hành lang Cẩm thạch"),
                             item(1, "Catacombs", "", "Hầm mộ")])
        self.assertFalse(result["issues"])
        self.assertEqual(result["area_names_in_source"], 2)
        self.assertFalse(result["layout_verified"])

    def test_mismatch_rejected(self):
        result = self.check([item(0, "Other", "Gallery", "Hành lang"),
                             item(1, "Catacombs", "", "Hầm mộ")])
        self.assertTrue(any("stale" in msg for msg in result["issues"]))

    def test_missing_index_rejected(self):
        result = self.check([item(0, "Marble", "Gallery", "Hành lang")])
        self.assertTrue(any("Missing" in msg for msg in result["issues"]))


if __name__ == "__main__":
    unittest.main()
