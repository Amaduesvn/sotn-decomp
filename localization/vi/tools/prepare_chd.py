#!/usr/bin/env python3
"""Safely prepare a local PS1 CHD for upstream sotn-decomp's US extraction.

Converts an optical-disc CHD into disks/sotn.us.cue + disks/sotn.us.bin
using MAME chdman. This *writes local commercial game data*; the project's
disks/ folder is gitignored, and you must NEVER upload these outputs to GitHub.

The conversion alone cannot prove the source is a valid US SLUS-00067 image.
"""
from __future__ import annotations

import argparse
import json
import shutil
import subprocess
from pathlib import Path

try:
    from .chd_preflight import CHDError, inspect_chd
    from .disc_preflight import DiscError, preflight
except ImportError:
    from chd_preflight import CHDError, inspect_chd
    from disc_preflight import DiscError, preflight


class PrepareError(ValueError):
    pass


def prepare_plan(chd: Path, repo: Path) -> dict:
    chd = chd.expanduser().resolve()
    repo = repo.expanduser().resolve()
    if not (repo / "Makefile").is_file() or not (repo / "config/assets.us.yaml").is_file():
        raise PrepareError(f"Not a sotn-decomp root: {repo}")
    header = inspect_chd(chd)
    target = repo / "disks"
    if not target.is_dir():
        raise PrepareError("Expected disks/ directory is missing")
    cue = target / "sotn.us.cue"
    binfile = target / "sotn.us.bin"
    for output in (cue, binfile):
        if output.exists():
            raise PrepareError(f"Refusing to overwrite existing game data: {output.name}")
    tool = shutil.which("chdman")
    return {
        "input_chd": str(chd),
        "chd_version": header["chd_version"],
        "output_cue": str(cue),
        "output_bin": str(binfile),
        "chdman": tool,
        "ready_to_convert": tool is not None,
        "game_serial_verified": False,
        "recommended_next_command": "make extract_disk",
        "warning": "Never commit BIN/CUE, extracted assets or copyrighted ROM files.",
    }


def extract_to_disks(chd: Path, repo: Path) -> dict:
    plan = prepare_plan(chd, repo)
    tool = plan["chdman"]
    if tool is None:
        raise PrepareError("chdman not found: install the MAME chdman tool first")
    target = repo.expanduser().resolve() / "disks"
    # Run under disks/ so the generated CUE references the adjacent BIN
    # using its plain file name rather than an absolute filesystem path.
    command = [
        tool, "extractcd", "-i", str(chd.expanduser().resolve()),
        "-o", "sotn.us.cue", "-ob", "sotn.us.bin",
    ]
    proc = subprocess.run(command, cwd=target, check=False, capture_output=True, text=True)
    if proc.returncode != 0:
        raise PrepareError(
            "chdman extraction failed (partial local outputs may remain): "
            + (proc.stderr or proc.stdout)[-1500:]
        )
    cue = target / "sotn.us.cue"
    if not cue.is_file():
        raise PrepareError("chdman returned success but CUE was not created")
    report = preflight(cue)
    return {
        "converted": True,
        "image_inspection": report,
        "upstream_next_commands": [
            "make extract_disk",
            "make extract -j",
            "make build -j",
            "make check",
        ],
        "game_serial_verified": False,
        "reminder": "Do not upload files from disks/ to the public repository.",
    }


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("chd", type=Path, help="Locally stored optical disc CHD")
    parser.add_argument("--repo-root", type=Path, default=Path(__file__).resolve().parents[3])
    parser.add_argument(
        "--extract", action="store_true",
        help="Actually decode CHD to ignored disks/ as BIN/CUE (default: only plan)",
    )
    args = parser.parse_args()
    try:
        result = (extract_to_disks(args.chd, args.repo_root) if args.extract
                  else prepare_plan(args.chd, args.repo_root))
    except (PrepareError, CHDError, DiscError, OSError) as exc:
        print(json.dumps({"error": str(exc)}, ensure_ascii=False))
        return 2
    print(json.dumps(result, ensure_ascii=False, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
