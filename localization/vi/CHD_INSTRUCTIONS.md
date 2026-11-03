# CHD → BIN/CUE for the PS1 US SOTN localization build

**Scope:** Local workflow for an owner-provided *Castlevania: Symphony of the Night* disc image. CHD is a lossless disc container commonly used with emulators. Unlike raw BIN/CUE, the disc sectors may be compressed.

**Safety:** The output contains proprietary commercial game content. Keep it local: do not upload the original CHD, extracted BIN/CUE, BIOS, or game assets to a public GitHub repository. The upstream repository's `disks/` directory is already gitignored.

## Step 1 — Inspect without converting

The CHD file can be identified by the header without MAME tools:

```sh
python3 localization/vi/tools/chd_preflight.py "/path/to/game.chd"
```

If MAME's `chdman` is installed, get additional media/track metadata:

```sh
python3 localization/vi/tools/chd_preflight.py "/path/to/game.chd" --chdman-info
```

**Neither operation proves the serial SLUS-00067.** The file's name is not evidence of the region. Do not infer region from CHD v5 SHA-1 fields alone.

## Step 2 — Extract to the exact location expected upstream

Install the `chdman` program from [MAME](https://www.mamedev.org/), e.g. on supported Ubuntu installations via the relevant MAME tools package.

Run the dry-run plan first:

```sh
python3 localization/vi/tools/prepare_chd.py "/path/to/game.chd"
```

Then, if the reported paths are correct:

```sh
python3 localization/vi/tools/prepare_chd.py "/path/to/game.chd" --extract
```

This runs the MAME `chdman extractcd` operation. It writes **only into the local, gitignored** `disks/` directory with filenames expected by upstream:

- `disks/sotn.us.cue`
- `disks/sotn.us.bin`

The helper refuses to overwrite existing output files and reports CUE/sector information. Its BIN preflight now also inspects ISO9660's SYSTEM.CNF boot entry when available; the field system_cnf_boot_serial should be SLUS_000.67 for the intended US reference. That boot string is a strong version clue but is NOT an authenticity proof. If conversion fails, partial files may be left behind; diagnose before retrying. You can alternatively extract manually:

```sh
cd disks
chdman extractcd -i "/absolute/path/to/game.chd" -o sotn.us.cue -ob sotn.us.bin
cd ..
```

The command-line flags above correspond to MAME's `extractcd` and `-ob` output-bin option. Do **not** assume extraction success means the game is the US edition.

## Step 3 — Build the unmodified game first

Follow upstream [Build Wiki](https://github.com/Xeeynamo/sotn-decomp/wiki/Build), including its dependency installation steps (Ubuntu 24.04, toolchains, submodules). Once your original US disc is at `disks/sotn.us.cue`:

```sh
make extract_disk
make extract -j
make build -j
```

Stop on errors. `make build -j` already performs checksum validation (unless `SKIP_CHECK` is set), through `tools/sotn-assets/build.go` and `check.go`. The Makefile currently has no `make check` target. A different region, fan-patched CHD, or an unmatched source revision may fail this check.

## Step 4 — Use the extracted game for Vietnamese localization

Once the baseline matches:

1. Extract item, enemy and cutscene text and graphics with the existing asset tools.
2. Validate the extended translation inventory and consolidate vocabulary.
3. Implement Vietnamese text encoding separately for 8×8 text, Shift-JIS-derived menu descriptions and cutscene display.
4. Build a tiny on-screen vertical slice and inspect in DuckStation.
5. Only then work toward a distributable ROM-free patch.

## Automated checks in the repository

The tests in `localization/vi/tests/test_chd_preflight.py` and `test_prepare_chd.py` use small synthetic headers only. Passing these tests does **not** authenticate any uploaded game image or prove a real CHD can be decoded in the current environment.

No actual retail game has been committed to this repository.
