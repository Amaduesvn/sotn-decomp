"""Tests for standard Vietnamese alphabet and PS1 glyph coverage metadata."""
import sys
import tempfile
import unittest
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from tools.charset import charset_report, vietnamese_alphabet  # noqa: E402


class CharsetTests(unittest.TestCase):
    def test_full_alphabet_contains_accents_and_d_stroke(self):
        chars = vietnamese_alphabet()
        self.assertEqual(len(chars), 186)
        for expected in ("a", "A", "ă", "Ă", "ấ", "Ắ", "ễ", "Ữ", "ỳ", "Ỵ", "đ", "Đ"):
            self.assertIn(expected, chars)

    def test_report_does_not_promise_build(self):
        with tempfile.TemporaryDirectory() as tmp:
            path = Path(tmp) / "tools/sotn-assets/sotn/string.go"
            path.parent.mkdir(parents=True)
            # Minimal valid 256-slot table for deterministic fixture testing.
            table = (
                'var psxFontTable = []rune(strings.Join([]string{\n'
                + chr(96) + "A" * 256 + chr(96) + '\n}, ""))'
            )
            path.write_text(table, encoding="utf-8")
            result = charset_report(Path(tmp))
        self.assertEqual(result["existing_mapped_positions"], 256)
        self.assertEqual(result["vietnamese_alphabet_letters"], 186)
        self.assertEqual(result["already_in_mapping"], 1)
        self.assertEqual(result["missing_from_mapping"], 185)


if __name__ == "__main__":
    unittest.main()
