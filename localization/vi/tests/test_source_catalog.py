"""Offline regression checks for indexed US source-text catalog."""
import csv
import io
import sys
import tempfile
import unittest
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from tools.source_catalog import (  # noqa: E402
    CatalogError, catalog, extract_array, serialize,
)

MAIN = '''
const char* g_MenuStr[] = {
    _S("ALUCARD"),
    _S("Button settings"),
    _S(""),
};
SpellDef g_SpellDefs[] = {
    {"Hellfire", _S("↑↓↘→"), "Transport and fireball attack", 15, 20},
    {"", _S(""), "", 0, 0},
};
RelicDesc g_RelicDefs[] = {
    {" Soul of Bat", "Transform into Bat", 256, 256, 0},
};
'''
SELECT = '''
StageName D_80180128[80] = {
    {_S("Marble"), _S("Gallery")},
    {_S("Entrance"), _S("")},
};
'''


class CatalogTests(unittest.TestCase):
    def test_keys_preserve_indices_and_originals(self):
        menu = extract_array(MAIN, "src/config_us.h", "g_MenuStr", "menu")
        self.assertEqual(
            [(r["key"], r["original"]) for r in menu],
            [("g_MenuStr[0].text", "ALUCARD"),
             ("g_MenuStr[1].text", "Button settings")],
        )

    def test_spell_and_relic_fields_do_not_touch_parameters(self):
        spells = extract_array(MAIN, "src/config_us.h", "g_SpellDefs", "spell")
        relics = extract_array(MAIN, "src/config_us.h", "g_RelicDefs", "relic")
        self.assertEqual(
            [(r["key"], r["original"]) for r in spells],
            [("g_SpellDefs[0].name", "Hellfire"),
             ("g_SpellDefs[0].description", "Transport and fireball attack")],
        )
        self.assertEqual(relics[1]["original"], "Transform into Bat")

    def test_stage_pair_indices(self):
        rows = extract_array(SELECT, "src/st/sel/2C048.c", "D_80180128", "stage")
        self.assertEqual([r["key"] for r in rows],
                         ["D_80180128[0].part1",
                          "D_80180128[0].part2",
                          "D_80180128[1].part1"])

    def test_unexpected_syntax_fails_loudly(self):
        malformed = MAIN.replace('_S("ALUCARD")', 'UNKNOWN("ALUCARD")')
        with self.assertRaises(CatalogError):
            extract_array(malformed, "src/config_us.h", "g_MenuStr", "menu")

    def test_csv_quoting_roundtrip(self):
        rows = extract_array(
            MAIN.replace('Button settings', 'Button, "revised" settings'),
            "src/config_us.h", "g_MenuStr", "menu"
        )
        saved = serialize(rows)
        recovered = list(csv.DictReader(io.StringIO(saved)))
        self.assertEqual(recovered[1]["original"], 'Button, "revised" settings')

    def test_integrated_fixture(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            (root / "src/st/sel").mkdir(parents=True)
            (root / "src/config_us.h").write_text(MAIN, encoding="utf-8")
            (root / "src/st/sel/2C048.c").write_text(SELECT, encoding="utf-8")
            rows = catalog(root)
        self.assertEqual(len(rows), 8)
        self.assertEqual(len({x["key"] for x in rows}), 8)


if __name__ == "__main__":
    unittest.main()
