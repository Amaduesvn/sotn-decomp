#!/usr/bin/env python3
"""Read CHD file headers without unpacking copyrighted game content.

Supports MAME CHD v3-v5 *header identification*. v5 gives useful header
metadata. PS1 region, serial, tracks and file integrity cannot be established
by a CHD header alone; use chdman info/extractcd to inspect the actual disc.

Reference: MAME chd.h and chd.cpp, CHD v5 header offsets.
"""
from __future__ import annotations

import argparse
import hashlib
import json
import shutil
import subprocess
from pathlib import Path

MAGIC = b"MComprHD"
HEADER_SIZES = {3: 120, 4: 108, 5: 124}
MAX_HEADER = 124


class CHDError(ValueError):
    pass


def be32(data: bytes, start: int) -> int:
    return int.from_bytes(data[start:start + 4], byteorder="big")


def be64(data: bytes, start: int) -> int:
    return int.from_bytes(data[start:start + 8], byteorder="big")


def identify_header(header: bytes) -> dict:
    if len(header) < 16 or header[:8] != MAGIC:
        raise CHDError("Not a CHD file (MComprHD signature missing)")
    header_size = be32(header, 8)
    version = be32(header, 12)
    if version not in HEADER_SIZES:
        raise CHDError(f"Unsupported CHD header version: {version}")
    if header_size != HEADER_SIZES[version]:
        raise CHDError(f"Unexpected v{version} CHD header length: {header_size}")
    if len(header) < header_size:
        raise CHDError("Truncated CHD file header")
    result = {
        "format": "CHD",
        "chd_version": version,
        "header_length": header_size,
        "game_serial_verified": False,
        "optical_disc_verified": False,
        "header_only": True,
    }
    if version == 5:
        logical_bytes = be64(header, 32)
        hunk_bytes = be32(header, 56)
        unit_bytes = be32(header, 60)
        if not all((logical_bytes, hunk_bytes, unit_bytes)):
            raise CHDError("Invalid CHD v5 logical/hunk/unit size")
        result.update({
            "logical_bytes": logical_bytes,
            "hunk_bytes": hunk_bytes,
            "unit_bytes": unit_bytes,
            "compression_codes": [
                header[offset:offset + 4].decode("ascii", errors="replace")
                for offset in (16, 20, 24, 28)
            ],
            "raw_sha1_from_header": header[64:84].hex(),
            "chd_sha1_from_header": header[84:104].hex(),
            "parent_sha1_from_header": header[104:124].hex(),
            "requires_parent": any(header[104:124]),
        })
    return result


def inspect_chd(path: Path, hash_full: bool = False) -> dict:
    if not path.is_file():
        raise CHDError(f"CHD file not found: {path.name}")
    size = path.stat().st_size
    with path.open("rb") as stream:
        header = stream.read(MAX_HEADER)
        result = identify_header(header)
        digest = None
        if hash_full:
            stream.seek(0)
            hasher = hashlib.sha256()
            for block in iter(lambda: stream.read(4 * 1024 * 1024), b""):
                hasher.update(block)
            digest = hasher.hexdigest()
    result.update({
        "filename": path.name,
        "compressed_file_bytes": size,
        "sha256_of_chd_file": digest,
        "note": (
            "Header signatures and embedded SHA-1 values do NOT establish "
            "that this is the US SLUS-00067 game, a complete disc, or an "
            "authentic dump. Decompression and game-file inspection are needed."
        ),
    })
    return result


def chdman_metadata(path: Path) -> dict:
    """Run chdman info safely, without invoking a shell or writing files."""
    executable = shutil.which("chdman")
    if executable is None:
        return {
            "available": False,
            "note": "Install MAME chdman to inspect CD tracks / decompress.",
        }
    try:
        command = subprocess.run(
            [executable, "info", "-i", str(path.resolve())],
            capture_output=True, text=True, timeout=60, check=False,
        )
    except (OSError, subprocess.TimeoutExpired) as exc:
        return {"available": True, "error": str(exc)}
    return {
        "available": True,
        "exit_code": command.returncode,
        "info_output": (command.stdout + command.stderr)[:12000],
        "note": "Informational only; it does not verify the retail region.",
    }


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("chd", type=Path, help="Local CHD file")
    parser.add_argument("--sha256", action="store_true", help="Hash full CHD file")
    parser.add_argument("--chdman-info", action="store_true", help="Include chdman media details")
    args = parser.parse_args()
    try:
        report = inspect_chd(args.chd, hash_full=args.sha256)
        if args.chdman_info:
            report["chdman"] = chdman_metadata(args.chd)
    except (CHDError, OSError) as exc:
        print(json.dumps({"error": str(exc)}, ensure_ascii=False))
        return 2
    print(json.dumps(report, indent=2, ensure_ascii=False))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
