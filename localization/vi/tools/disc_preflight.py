#!/usr/bin/env python3
"""Non-destructive preflight inspection of a local PS1 disc BIN/CUE or ISO.

This is a heuristic format check, NOT proof of an authentic SLUS-00067 dump.
It never modifies the game image and must not be used to distribute ROM data.
"""
from __future__ import annotations

import argparse
import hashlib
import json
import re
from pathlib import Path

SECTOR_RAW = 2352
SECTOR_ISO = 2048
BOOT_PATTERN = re.compile(rb"SLUS[_-]000[.]?67", re.IGNORECASE)
CUE_FILE_PATTERN = re.compile(
    r'^\s*FILE\s+(?:"([^"]+)"|(\S+))\s+BINARY\s*$', re.IGNORECASE
)
CUE_TRACK_PATTERN = re.compile(
    r'^\s*TRACK\s+(\d+)\s+(MODE1/2352|MODE2/2352|AUDIO|MODE1/2048)\s*$',
    re.IGNORECASE,
)


class DiscError(ValueError):
    pass


def cue_sources(source: str) -> tuple[list[str], list[dict]]:
    files = []
    tracks = []
    current = None
    for line_no, line in enumerate(source.splitlines(), 1):
        line = line.strip()
        file_match = CUE_FILE_PATTERN.fullmatch(line)
        track_match = CUE_TRACK_PATTERN.fullmatch(line)
        if file_match:
            current = file_match.group(1) or file_match.group(2)
            files.append(current)
        elif track_match:
            if current is None:
                raise DiscError(f"TRACK without preceding FILE at line {line_no}")
            tracks.append({
                "number": int(track_match.group(1)),
                "type": track_match.group(2).upper(),
                "file": current,
            })
    if not files or not tracks:
        raise DiscError("No supported FILE BINARY / TRACK entries in CUE")
    return list(dict.fromkeys(files)), tracks


SYSTEM_CNF_BOOT_PATTERN = re.compile(
    rb"\bBOOT2?\s*=\s*cdrom\s*:\s*\\*\s*([A-Z]{4}[_-]\d{3}[.]\d{2})",
    re.IGNORECASE,
)


def _read_sector(stream, lba: int, stride: int, user_offset: int) -> bytes:
    """Read one 2048-byte user-data sector without modifying the image."""
    stream.seek(lba * stride + user_offset)
    return stream.read(SECTOR_ISO)


def _read_extent(stream, lba: int, size: int, stride: int, user_offset: int) -> bytes:
    """Read a bounded extent from an ISO9660 data track."""
    if lba < 0 or size <= 0 or size > 65536:
        return b""
    chunks = []
    for block in range((size + SECTOR_ISO - 1) // SECTOR_ISO):
        payload = _read_sector(stream, lba + block, stride, user_offset)
        if len(payload) != SECTOR_ISO:
            return b""
        chunks.append(payload)
    return b"".join(chunks)[:size]


def _directory_entry_extent(record: bytes) -> tuple[int, int] | None:
    if len(record) < 34 or record[0] < 34 or len(record) < record[0]:
        return None
    lba = int.from_bytes(record[2:6], "little")
    size = int.from_bytes(record[10:14], "little")
    return lba, size


def _read_system_cnf_serial(stream, stride: int, user_offset: int) -> str | None:
    """Inspect SYSTEM.CNF through ISO9660 records rather than guessing by filename.

    Handles common single-data-track images and does not authenticate disc
    provenance. A successful read is evidence of the BOOT entry only.
    """
    pvd = _read_sector(stream, 16, stride, user_offset)
    if len(pvd) != SECTOR_ISO or pvd[:7] != b"\x01CD001\x01":
        return None
    root_length = pvd[156]
    root = _directory_entry_extent(pvd[156:156 + root_length])
    if root is None:
        return None
    directory = _read_extent(stream, *root, stride, user_offset)
    pos = 0
    while pos < len(directory):
        length = directory[pos]
        if length == 0:
            pos = ((pos // SECTOR_ISO) + 1) * SECTOR_ISO
            continue
        if pos + length > len(directory) or length < 34:
            return None
        record = directory[pos:pos + length]
        name_length = record[32]
        name = record[33:33 + name_length].upper()
        if name in {b"SYSTEM.CNF", b"SYSTEM.CNF;1"}:
            extent = _directory_entry_extent(record)
            if extent is None:
                return None
            text = _read_extent(stream, *extent, stride, user_offset)
            match = SYSTEM_CNF_BOOT_PATTERN.search(text)
            return match.group(1).decode("ascii").upper() if match else None
        pos += length
    return None


def inspect_image(path: Path, hash_full: bool = False) -> dict:
    if not path.is_file():
        raise DiscError(f"Image not found: {path.name}")
    length = path.stat().st_size
    if length == 0:
        raise DiscError(f"Empty file: {path.name}")
    # ISO9660 Primary Volume Descriptor at logical sector 16. The payload
    # begins after the sector header: 16 bytes for mode 1, 24 for CD-XA mode 2.
    options = [
        (SECTOR_RAW, 16, "mode1_raw_2352"),
        (SECTOR_RAW, 24, "mode2_raw_2352"),
        (SECTOR_ISO, 0, "iso_2048"),
    ]
    candidates = []
    with path.open("rb") as stream:
        for stride, start, label in options:
            stream.seek(16 * stride + start + 1)
            if stream.read(5) == b"CD001":
                candidates.append(label)
        serial_from_system_cnf = None
        for stride, start, label in options:
            if label in candidates:
                serial_from_system_cnf = _read_system_cnf_serial(stream, stride, start)
                if serial_from_system_cnf:
                    break
        stream.seek(0)
        sample = stream.read(min(length, 4 * 1024 * 1024))
        serial_in_sample = bool(BOOT_PATTERN.search(sample))
        digest = None
        if hash_full:
            stream.seek(0)
            hasher = hashlib.sha256()
            for block in iter(lambda: stream.read(4 * 1024 * 1024), b""):
                hasher.update(block)
            digest = hasher.hexdigest()
    return {
        "filename": path.name,
        "bytes": length,
        "multiple_of_2352": length % SECTOR_RAW == 0,
        "multiple_of_2048": length % SECTOR_ISO == 0,
        "iso9660_pvd_candidates": candidates,
        "us_serial_seen_in_first_4mib": serial_in_sample,
        "system_cnf_boot_serial": serial_from_system_cnf,
        "matches_us_reference_boot_name": serial_from_system_cnf == "SLUS_000.67",
        "sha256": digest,
        "note": (
            "Serial and PVD heuristics are not sufficient to authenticate a "
            "retail game dump; compare against the project's known-good image "
            "and run the upstream extractor before patching."
        ),
    }


def preflight(path: Path, hash_full: bool = False) -> dict:
    if path.suffix.lower() == ".cue":
        if not path.is_file():
            raise DiscError("CUE file does not exist")
        files, tracks = cue_sources(path.read_text(encoding="utf-8-sig"))
        # Resolve only local files referenced by the CUE, never remote URLs.
        disc_dir = path.parent.resolve()
        image_paths = [(disc_dir / name).resolve() for name in files]
        if any(not img.is_relative_to(disc_dir) for img in image_paths):
            raise DiscError("CUE references an image outside the CUE directory")
        images = [inspect_image(img, hash_full) for img in image_paths]
        return {
            "input": path.name,
            "format": "cue",
            "tracks": tracks,
            "images": images,
            "non_destructive": True,
        }
    if path.suffix.lower() not in {".bin", ".iso", ".img"}:
        raise DiscError("Expected .cue, .bin, .img, or .iso")
    return {
        "input": path.name,
        "format": "image",
        "images": [inspect_image(path, hash_full)],
        "non_destructive": True,
        "cue_note": "A separate CUE is helpful for multiple tracks and CD audio.",
    }


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("disc", type=Path, help="Local CUE or disc image")
    parser.add_argument("--sha256", action="store_true", help="Hash entire image (slow on large files)")
    args = parser.parse_args()
    try:
        report = preflight(args.disc, args.sha256)
    except (DiscError, UnicodeError, OSError) as exc:
        print(json.dumps({"error": str(exc)}, ensure_ascii=False))
        return 2
    print(json.dumps(report, indent=2, ensure_ascii=False))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
