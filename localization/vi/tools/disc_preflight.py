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
        images = [inspect_image(path.parent / name, hash_full) for name in files]
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
