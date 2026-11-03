"""Pure fake-file tests for CHD v3/v4/v5 identification and optional chdman."""
import sys
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from tools.chd_preflight import (  # noqa: E402
    CHDError,
    chdman_metadata,
    identify_header,
    inspect_chd,
)


def fake_header(version=5, length=124):
    data = bytearray(length)
    data[:8] = b"MComprHD"
    data[8:12] = length.to_bytes(4, "big")
    data[12:16] = version.to_bytes(4, "big")
    if version == 5:
        data[16:20] = b"cdzl"
        data[32:40] = (800000000).to_bytes(8, "big")
        data[56:60] = (18816).to_bytes(4, "big")
        data[60:64] = (2352).to_bytes(4, "big")
        data[64:84] = bytes.fromhex("ab" * 20)
    return bytes(data)


class CHDPreflightTests(unittest.TestCase):
    def test_v5_header_metadata(self):
        report = identify_header(fake_header())
        self.assertEqual(report["chd_version"], 5)
        self.assertEqual(report["logical_bytes"], 800000000)
        self.assertEqual(report["hunk_bytes"], 18816)
        self.assertEqual(report["unit_bytes"], 2352)
        self.assertFalse(report["game_serial_verified"])
        self.assertFalse(report["requires_parent"])

    def test_old_versions_identified_without_fake_v5_fields(self):
        for version, length in ((3, 120), (4, 108)):
            result = identify_header(fake_header(version, length))
            self.assertEqual(result["chd_version"], version)
            self.assertNotIn("logical_bytes", result)

    def test_reject_non_chd_and_bad_length(self):
        with self.assertRaises(CHDError):
            identify_header(b"INVALID!!")
        with self.assertRaisesRegex(CHDError, "length"):
            identify_header(fake_header(5, 120))

    def test_reject_truncated_header(self):
        with self.assertRaisesRegex(CHDError, "Truncated"):
            identify_header(fake_header()[:70])

    def test_reject_zero_hunk_size(self):
        bad = bytearray(fake_header())
        bad[56:60] = bytes(4)
        with self.assertRaises(CHDError):
            identify_header(bad)

    def test_file_inspection_uses_only_header(self):
        with tempfile.TemporaryDirectory() as tmp:
            path = Path(tmp) / "dummy.chd"
            path.write_bytes(fake_header() + bytes(100))
            result = inspect_chd(path, hash_full=True)
        self.assertEqual(result["compressed_file_bytes"], 224)
        self.assertEqual(len(result["sha256_of_chd_file"]), 64)

    def test_chdman_missing_is_not_fatal(self):
        with patch("tools.chd_preflight.shutil.which", return_value=None):
            result = chdman_metadata(Path("dummy.chd"))
        self.assertFalse(result["available"])


if __name__ == "__main__":
    unittest.main()
