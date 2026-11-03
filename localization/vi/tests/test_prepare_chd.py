"""No-ROM safety tests for converting private CHD to upstream disks/ layout."""
import sys
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from tools.prepare_chd import PrepareError, prepare_plan, extract_to_disks  # noqa: E402


def make_fixture(root):
    root = Path(root)
    (root / "config").mkdir()
    (root / "disks").mkdir()
    (root / "Makefile").write_text("", encoding="utf-8")
    (root / "config/assets.us.yaml").write_text("version: us\n", encoding="utf-8")
    chd = root / "owner.chd"
    data = bytearray(124)
    data[:8] = b"MComprHD"
    data[8:12] = (124).to_bytes(4, "big")
    data[12:16] = (5).to_bytes(4, "big")
    data[32:40] = (700_000_000).to_bytes(8, "big")
    data[56:60] = (18816).to_bytes(4, "big")
    data[60:64] = (2352).to_bytes(4, "big")
    chd.write_bytes(data)
    return chd


class PrepareTests(unittest.TestCase):
    def test_plan_is_read_only_and_detects_chdman(self):
        with tempfile.TemporaryDirectory() as temp:
            root = Path(temp)
            chd = make_fixture(root)
            with patch("tools.prepare_chd.shutil.which", return_value="/usr/bin/chdman"):
                report = prepare_plan(chd, root)
            self.assertTrue(report["ready_to_convert"])
            self.assertFalse(report["game_serial_verified"])
            self.assertFalse((root / "disks/sotn.us.bin").exists())
            self.assertFalse((root / "disks/sotn.us.cue").exists())

    def test_missing_chdman_is_explained(self):
        with tempfile.TemporaryDirectory() as temp:
            root = Path(temp)
            chd = make_fixture(root)
            with patch("tools.prepare_chd.shutil.which", return_value=None):
                report = prepare_plan(chd, root)
                with self.assertRaisesRegex(PrepareError, "chdman not found"):
                    extract_to_disks(chd, root)
            self.assertFalse(report["ready_to_convert"])

    def test_refuses_to_overwrite_existing_bin(self):
        with tempfile.TemporaryDirectory() as temp:
            root = Path(temp)
            chd = make_fixture(root)
            (root / "disks/sotn.us.bin").write_bytes(b"private")
            with self.assertRaisesRegex(PrepareError, "overwrite"):
                prepare_plan(chd, root)

    def test_refuses_invalid_repository_root(self):
        with tempfile.TemporaryDirectory() as temp:
            root = Path(temp)
            chd = root / "dummy.chd"
            chd.write_bytes(b"MComprHD")
            with self.assertRaisesRegex(PrepareError, "Not a sotn-decomp root"):
                prepare_plan(chd, root)


if __name__ == "__main__":
    unittest.main()
