# PS1 US Vietnamese Font and Text Integration

**State:** source investigation only. No ROM-based compilation, visual test, or released patch.
**Target:** PS1 US SLUS-00067.

## Confirmed implementation details

- tools/sotn-assets/sotn/string.go uses a 256-position PS1 8x8 text mapping. Its encoder rejects characters not present in that mapping.
- In the same module, menu descriptions are encoded separately with a Shift-JIS-compatible path (EncodeMenuDescription). Modifying the 8x8 mapping alone cannot fix those descriptions.
- src/dra/menu.c contains original US settings labels and several rendering routines. Our menu_draft.csv is *not* yet wired into the executable.
- config/assets.us.yaml identifies stage-title graphics such as gfx_stage_name_en. Area names are therefore not all plain editable strings.
- tools/sotn-assets/assets/cutscene/handler.go represents dialogue as TEXT plus control instructions. Preserve line breaks, events, voice and timing instructions when localizing.
- The upstream repository intentionally omits proprietary game assets required to build the original binary.

## Verified character counts

- Current PS1 mapping: 256 entries, 254 distinct glyph values.
- Complete modern Vietnamese alphabet: 186 upper/lowercase letters with tones, vowel variants and Đ/đ.
- Present in existing mapping: 52 unaccented Latin letters.
- Missing from existing mapping: **134 Vietnamese alphabetic characters**.
- The first 6 settings translations all contain one or more missing glyphs.

These are **encoding-table** counts, not visual/font texture validation. The
table contains Japanese characters, UI symbols and icons; replacing entries
indiscriminately could damage existing menus and scripted text. The 0xFF
byte also acts as a string control/terminator in this system.

## Candidate approaches (not yet implemented)

| Approach | Advantage | Risk or unknown |
| --- | --- | --- |
| Remap unused byte codes to Vietnamese glyphs | Smaller modifications | Must identify genuinely unused codes and edit the corresponding atlas |
| Draw tone marks / vowel marks dynamically | Fewer added glyphs | 8x8 readability, vertical alignment and renderer behavior are untested |
| Add a multibyte encoding | Full alphabet capacity | Requires changes across each text renderer and size calculation |
| Replace rendered stage-title graphics | Can preserve original presentation | Requires original extracted assets and graphics rebuild |

## First in-game prototype checklist

1. Extract assets locally from a legitimately obtained US SLUS-00067 disc.
2. Confirm the build reproduces the original binary before any localization.
3. Render a short test line containing uppercase/lowercase and all six tones.
4. Test one menu label, one character dialogue line, and an equipment description.
5. Verify readability, clipping, line timing and game stability on DuckStation.
6. Expand only after the test path succeeds.

## Checks available without game files

    python3 localization/vi/tools/audit.py --json
    python3 localization/vi/tools/charset.py
    python3 -m unittest discover -s localization/vi/tests -v

These commands check sources and encoding gaps. They do not patch or compile
the game, and have not yet been verified as passing in a CI run.

Do not commit original ROM/ISO/BIN/CUE, extracted copyrighted assets, or BIOS
images. Distribute only a patch plus checksum and version instructions when
validated.
