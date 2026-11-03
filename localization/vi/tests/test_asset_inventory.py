"""Asset inventory parsing: no retail data required."""
import sys
import unittest
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from tools.asset_inventory import inventory  # noqa: E402


class InventoryTests(unittest.TestCase):
    def test_counts_and_targets(self):
        source = """
version: us
files:
  - target: disks/us/DRA.BIN
    segments:
      - [0x4B04, equipment, us/equipment]
      - [0x7718, accessories, us/accessories]
      # - [0x1234, cutscene, not_active]
  - target: disks/us/ST/TEST/TEST.BIN
    segments:
      - [0x13F0, cutscene, cutscene_data]
      - [0x521C, cmpgfx, gfx_stage_name_en, 128, 128, 4]
      - [0x6000, cmpgfx, gfx_enemy, 128, 128, 4]
"""
        report = inventory(source)
        self.assertEqual(report["declared_asset_count"], 4)
        self.assertEqual(
            report["declared_assets_by_type"],
            {"accessories": 1, "cutscene": 1, "equipment": 1, "stage_name_graphic": 1},
        )
        self.assertEqual(report["sources"][0]["target"], "disks/us/DRA.BIN")
        self.assertEqual(report["sources"][2]["target"], "disks/us/ST/TEST/TEST.BIN")

    def test_empty_inventory_does_not_claim_coverage(self):
        report = inventory("version: us\nfiles:\n")
        self.assertEqual(report["declared_asset_count"], 0)
        self.assertIn("not string counts", report["limitation"])


if __name__ == "__main__":
    unittest.main()
