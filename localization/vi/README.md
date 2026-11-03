# SOTN Vietnamese Localization (PS1 US)

> **Status: project initialized; translation prototype only.** This directory does not contain a working patch or a verified in-game Vietnamese font.

## Scope

- Target: **Castlevania: Symphony of the Night**, PlayStation 1 **US (SLUS-00067)**.
- Deliverables: editable Vietnamese localization data, font/encoding changes, automated checks, and ultimately a patch applied to a user's own copy of the original game.
- Preserve the original decompilation work and keep localization changes on the `vi-localization` branch until validated.
- Do **not** commit any commercial ROM/ISO/BIN/CUE, extracted proprietary assets, or BIOS images.

## Confirmed source locations

| Component | Current source/tool | Verified repository capability |
| --- | --- | --- |
| Equipment names and descriptions | `tools/sotn-assets/assets/itemdefs/handler.go` | Extract/build YAML models; 217 equipment records |
| Accessory names and descriptions | `tools/sotn-assets/assets/itemdefs/handler.go` | Extract/build YAML models; 90 accessory records |
| Enemy names | `tools/sotn-assets/assets/enemydefs/handler.go` | Extract/build YAML models; 400 enemy slots by default |
| Cutscene scripts | `tools/sotn-assets/assets/cutscene/handler.go` | Extract/build script commands and text |
| Menu | `src/dra/menu.c` | C strings and menu drawing routines |
| Text encoding | `tools/sotn-assets/sotn/string.go` | PS1 8x8 font mapping and Shift-JIS-based menu descriptions |
| Area title graphics | `config/assets.us.yaml` | Graphic assets for stage names are identified |

These findings prove that the data and renderer can be investigated, **not** that Vietnamese text can already be rendered correctly.

## Implementation milestones

1. **Inventory:** Extract all translatable strings from a legitimately obtained PS1 US copy; record source paths, string IDs, limitations, and byte lengths.
2. **Font prototype:** Create a Vietnamese glyph atlas / encoding approach, map render paths (8x8 text, menu descriptions, dialogue, stage banners), and verify glyph rendering.
3. **Vertical slice:** Integrate a short dialogue, menu labels, one equipment name and description; rebuild and test in DuckStation.
4. **Coverage:** Expand to story, items, enemies, relics, spells, interface, stages, credits, and remaining graphics.
5. **QA and distribution:** Check overflows, events, line breaks, encoding round trips and compatibility; distribute only a ROM-free patch and instructions.

## Translation policy

- Keep canonical character names consistent (Alucard, Richter, Maria, Dracula).
- Prefer natural Vietnamese over word-for-word translation.
- Preserve control sequences, timing, sound cues and script branching.
- Keep strings short enough for the actual screen layout; measure and test rather than assuming English byte limits apply to Vietnamese.
- Track each candidate as `draft`, `reviewed`, or `tested_in_game`. A translated CSV row does not imply that it is installed in the build.

## Initial translation data

`menu_draft.csv` contains a **small provisional translation sample** copied from the US menu source. It is not yet wired into the executable and uses UTF-8 only as an authoring format.

## Build prerequisites

The upstream repository states that it does not bundle game assets or assembly code required to reconstruct the binaries. Local extraction/build and final patch validation will need the user's own copy of the reference game (SLUS-00067).

Upstream: https://github.com/Xeeynamo/sotn-decomp

This directory is part of a fork of that open-source decompilation. Follow the repository's existing license and preserve upstream attribution.
