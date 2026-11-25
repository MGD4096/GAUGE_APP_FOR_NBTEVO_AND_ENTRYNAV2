---
name: python-asset-generator
description: Good Python practices for make_db.py, the generator of GaugeApp's look (XML, ids header, frame packs, text/image DBs, previews). Use when changing layout, texts, ids, screens or the pack format, or when refactoring the generator.
---

# make_db.py: one source of truth, deterministic output

`make_db.py` turns a layout description into everything the car loads and into `src/gauge_ids.hpp`, which the C++
code compiles against. Its outputs are committed, so a bad generator change ships silently unless the generator
itself refuses to produce bad output.

## Structure

- Entry point under `if __name__ == "__main__": main()`; `main()` only parses arguments (`argparse`) and calls
  functions. Importing the module must have no side effects (no drawing, no file writes).
- Separate the stages: **model** (layout data, ids) → **validation** → **rendering** (Pillow) → **writing** (files).
  `--layout-only` should simply skip rendering, not take a different code path for ids.
- Pure functions that take data and return strings / bytes (`state(...)`, `screen_options(...)`) are easy to test;
  keep file I/O at the edges.
- Group related constants in one structure instead of many module globals: `make_db.py` has a frozen `Screen`
  dataclass and `SCREEN_LIST` (key, state, action, text model, text id, title, slot list) instead of parallel lists,
  which are a classic source of off-by-one errors. Do the same for the next family of related constants.
- Anything the C++ side needs (ids, counts, titles) is **exported into `gauge_ids.hpp`** from the same data, never
  retyped in C++.

## Design: SOLID for a generator script

- **S:** one module (or at least one clearly separated section) per stage – `layout` (data, ids), `validate`, `draw`
  (Pillow, one function per kind of frame), `emit` (XML, header, text DB), `pack` (frame packs, zips). A drawing
  function never builds XML; an XML function never opens a font.
- **O:** a new screen or frame family is a new **entry** (`Screen(...)` in the screens list, a row in
  `image_ranges()`, a slot list) that every stage picks up by iterating, not new `if screen == 3` branches in each
  stage. The same for languages: iterate `UI_LANGS`.
- **L / I:** every drawer has the same shape (`draw_x(fp, spec) -> {frame_id: Image}`) so the pack writer can treat
  them alike; pass a drawer the spec it uses (its box, font size, colour), not the whole module state.
- **D:** stages receive their inputs as arguments (layout, font path, output directory) instead of reading globals
  and `HERE`; `main()` wires them together. That is what makes the stages unit-testable without Pillow or files.

## Validation (fail loudly, before writing anything)

- `assert` / raise `SystemExit("...")` on (✓ = `make_db.py` does it):
  - ✓ duplicate XML ids and references that point nowhere (`action`, `model`, `target`, `parentId`) – `check_xml`;
  - ✓ more than `MAX_IMAGES_PER_STATE` (60) images in one HMI state – `check_xml`;
  - ✓ non-ASCII XML and text DB texts – `check_xml`, `write_texts`;
  - ✓ overlapping image id ranges – one table, `image_ranges()`, checked pairwise by `check_image_ranges()`; a new
    frame family gets a line there first;
  - ✓ drawn frames outside every declared range, or one id in two packs – `check_frames` (full run only);
  - a frame that is referenced but not drawn, or a pack above `kFramesMax` (16 MB);
  - layout pieces outside the visible area (~1250 × 470 px after `SCALE` and `ORIGIN`).
- ✓ Validate the generated XML by parsing it back (`xml.etree.ElementTree.fromstring`) before writing. (It found a
  `--` inside the XML header comment, which XML forbids; HmiMain3D tolerated it.)

## Deterministic, reproducible output

- Same input → byte-identical files (true today: a full run reproduces every committed pack, zip and preview):
  iterate over `sorted()` keys, fix zip timestamps (`ZipInfo` with a constant
  `date_time`), no `time.time()`, no random values, no dict-order dependence on older Pythons.
- Write each output through a temporary file + `os.replace`, so an interrupted run never leaves a half-written XML
  or pack.
- Write text files with explicit `encoding="utf-8"` and `newline="\n"`. `.gitattributes` keeps every text file LF
  in the repo and the working tree (`* text=auto eol=lf`), only `*.bat` CRLF, and marks generated binaries
  (`*.bin`, `*.zip`, `*.png`) `binary`; a new generated file type gets a line there.
- Print a short summary (counts, sizes) so a diff in the summary is visible in review.

## Python style

- Python 3.8+; type hints on public functions; `pathlib.Path` for paths relative to the script
  (`Path(__file__).resolve().parent`), never the current working directory.
- f-strings instead of `%` formatting in new code; for XML prefer `xml.etree.ElementTree` or one small helper that
  escapes attributes (`xml.sax.saxutils.quoteattr`) over hand-built strings.
- Small functions (≤ ~50 lines); name drawing helpers after what they draw.
- **The language is a value, never a flag**: pass `lang` (`"pl"`, `"en"`, as `background(fp, lang)` does), never
  `is_polish=True` / `english=False`. `make_db.py` keeps every text in `TEXTS[lang]` (one complete block per
  language, so a translator copies one block) and the languages in `UI_LANG_DEFS` (code, `vehicle.language` values,
  text DB files; `LANGS` is the text DB's list of iDrive language files). The index in `UI_LANG_DEFS` is the frame
  offset; the generator exports the C++ enum `UiLang`, `uiLangForVehicle`, `kUiLangCount`, `kStatusLangStride` and
  the per-language tables (`kEngineBackground`, `kPsUnit`, `kScreenTitles`), so C++ holds nothing per language.
  Per-language properties ("KM" vs "PS") are entries of the block too, never `if lang == "pl"` branches.
- `check_texts()` runs before anything is written: same keys and list lengths in every block, ASCII text DB texts,
  a known power unit, no `vehicle.language` value or text DB file in two languages.
- No bytecode in the repo: `__pycache__/` and `*.pyc` are in `.gitignore`.
- Lint with `python3 -m pyflakes make_db.py` (or ruff) before committing.

## Tests for the generator

- A quick check runnable without Pillow: `python3 make_db.py --layout-only` followed by the validation above.
- A unit test module (`tests/test_make_db.py`, `python3 -m unittest`) for the pure parts: id allocation, XML of one
  state, settings page order, OPTION menus (exactly one Settings entry, only in state 10).
- After any visual change, look at `res/preview*.png`.

## Where GaugeApp differs today

- `make_db.py` is ~1580 lines with ~110 module-level constants and parallel lists per screen; all stages in one file
  and reading module globals (S, D). Per-screen drawing and preview values are still `if screen == k` branches
  (`s_background`, `screen_preview`) (O).
- XML is built with `%` string formatting; attributes are not escaped (safe only because all texts are ASCII
  literals, which `check_xml` enforces).
- The engine screen's background ids are not one `base + lang` range (`IMG_BG`, `IMG_BG_EN`, then the ids after
  it, `engine_background()`), kept for compatibility with the installed packs.
- Outputs are written in place, not through a temporary file + `os.replace`.
- No check for referenced-but-undrawn frames, pack size or layout bounds; no type hints, no unit tests.
