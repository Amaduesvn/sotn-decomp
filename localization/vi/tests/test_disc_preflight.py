"""Fake-sector fixtures for the non-destructive PS1 disc preflight utility."""
import sys
import tempfile
import unittest
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from tools.disc_preflight import DiscError, cue_sources, inspect_image, preflight  # noqa: E402


class DiscPreflightTests(unittest.TestCase):
    @staticmethod
    def synthetic_image(root: Path) -> Path:
        file = root / "test disc.bin"
        buffer = bytearray(2352 * 20)
        buffer[16 * 2352 + 24 + 1:16 * 2352 + 24 + 6] = b"CD001"
        buffer[100:111] = b"SLUS_000.67"
        file.write_bytes(buffer)
        return file

    def test_image_header_and_serial(self):
        with tempfile.TemporaryDirectory() as tmp:
            file = self.synthetic_image(Path(tmp))
            result = inspect_image(file)
        self.assertTrue(result["multiple_of_2352"])
        self.assertEqual(result["iso9660_pvd_candidates"], ["mode2_raw_2352"])
        self.assertTrue(result["us_serial_seen_in_first_4mib"])
        self.assertIsNone(result["sha256"])

    def test_optional_hash(self):
        with tempfile.TemporaryDirectory() as tmp:
            file = self.synthetic_image(Path(tmp))
            result = inspect_image(file, hash_full=True)
        self.assertEqual(len(result["sha256"]), 64)

    def test_cue_file_with_spaces_and_multiple_tracks(self):
        files, tracks = cue_sources(
            'FILE "test disc.bin" BINARY\n'
            '  TRACK 01 MODE2/2352\n'
            '  TRACK 02 AUDIO\n'
        )
        self.assertEqual(files, ["test disc.bin"])
        self.assertEqual([x["type"] for x in tracks], ["MODE2/2352", "AUDIO"])

    def test_cue_reads_local_image_without_modification(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            image = self.synthetic_image(root)
            original = image.read_bytes()
            cue = root / "test.cue"
            cue.write_text(
                'FILE "test disc.bin" BINARY\n'
                '  TRACK 01 MODE2/2352\n',
                encoding="utf-8",
            )
            report = preflight(cue)
            self.assertEqual(report["format"], "cue")
            self.assertEqual(len(report["tracks"]), 1)
            self.assertEqual(original, image.read_bytes())

    def test_reject_cue_path_traversal(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp) / "disc"
            root.mkdir()
            cue = root / "test.cue"
            cue.write_text('FILE "../private.bin" BINARY\\n  TRACK 01 MODE2/2352\\n')
            with self.assertRaisesRegex(DiscError, "outside"):
                preflight(cue)

    def test_reject_missing_file(self):
        with tempfile.TemporaryDirectory() as tmp:
            with self.assertRaises(DiscError):
                inspect_image(Path(tmp) / "missing.bin")

    def test_reject_cue_without_tracks(self):
        with self.assertRaises(DiscError):
            cue_sources('FILE "test disc.bin" BINARY\n')


if __name__ == "__main__":
    unittest.main()
