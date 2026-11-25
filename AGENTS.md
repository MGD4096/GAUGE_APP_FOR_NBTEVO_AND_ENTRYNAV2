# AGENTS.md

Guide for coding agents working on **GaugeApp**: a native iDrive PluginApp (gauge screens) for BMW **NBT Evo**
(QNX 6.5) and **EntryNav2 / EntryEVO** (Linux ARMv7 hard-float), built from one C++98 source. The maintainer writes in
Polish; README_PL.md and docs/*.md are Polish, README.md is the short English version.

## Layout

| Path | What |
|---|---|
| `src/engine_data.cpp` | the plugin: framework glue (own `PluginApp` vtable, `Runnable` stand-in, `pluginAppInfo`), CDS subscription, frame packs, rendering, settings, logging, crash guard |
| `src/cds_values.hpp` | CDS property list (`enum Prop`), parsing (`apply`), `Metrics`, run maxima |
| `src/drive_stats.hpp` | g per direction, torque envelope (engine load), fuel counter calibration, trip, performance timing |
| `src/gauge_view.hpp` | engine screen (screen 0): settings, units, frame id of every slot |
| `src/screens_view.hpp` | screens 1..4 (Driving, Fuel and trip, Performance, Warm-up): frame id of every slot |
| `src/gauge_ids.hpp` | **generated** by `make_db.py` – never edit by hand |
| `make_db.py` | the single source of the look: layout, texts, XML, ids header, frame packs, previews |
| `GaugeApp.xml`, `GaugeApp_ALL_*.zip`, `GaugeApp_frames*.bin`, `res/preview*.png` | **generated**, committed so a build needs no Pillow |
| `GaugeApp.manifest` | plugin manifest (Etch connector id 211) |
| `tests/` | host tests against a fake framework (`fake_appframework.*`) |
| `toolchain/` | Docker image for EntryNav2 (Ubuntu 12.04, armhf GCC 4.6, eglibc 2.15) |
| `build_nbt.bat` | NBT Evo build with QNX SDP 6.5 `qcc` on Windows |
| `build_entryNav2.bat` | EntryNav2 package on Windows: starts Docker Desktop, builds the toolchain image once, `make entrynav2-dist`, GLIBC check; `test` = `make check` in WSL first |
| `lib/NBT_evo_libs`, `lib/Entry_Evo_libs` | the cars' `libAppFramework.A.so` / `libCoreFramework.A.so` – BMW files, not ours: git-ignored, never commit or redistribute. How to copy them from a unit: README_PL.md, "Biblioteki BMW (`lib/`)" |
| `docs/` | installation guides (Polish) |

## Commands

Environment: Windows + PowerShell; Linux tools run in WSL (`wsl -e bash script.sh`; write scripts with LF endings to a
temp folder rather than inlining long quoted commands). Docker runs from PowerShell (no WSL integration).

- Regenerate after any look / layout / text / id change (needs Pillow + DejaVu Sans, takes a few minutes):
  `python3 make_db.py` (in WSL). `--layout-only` writes only `GaugeApp.xml` and `src/gauge_ids.hpp` (fast, no Pillow).
- Host tests (always run before finishing): `make check` (in WSL). Builds both variants with `-std=gnu++98` and runs
  `test_cds_values`, `app_host_test` (NBT + EntryNav2) and the EntryNav2 crash-guard check.
- EntryNav2 package: `docker run --rm -v "<project>:/work" -w /work gauge-entrynav2-tc make entrynav2-dist`
  → `dist/gauge-app-entrynav2.tar`. Check the result only needs `GLIBC_2.4`
  (`arm-linux-gnueabihf-objdump -T build/entrynav2/libGaugeApp.so`). Image: `docker build -t gauge-entrynav2-tc toolchain`.
- Windows shortcut for all of the above: `build_entryNav2.bat test` (tests in WSL, then the package).
- NBT Evo: `build_nbt.bat [QNX folder]` → `dist\nbt\GaugeApp` (no QNX on the dev PC: untested there).
- `build/`, `dist/`, `diag/` are git-ignored; Docker may create them as root.

## Hard constraints (learned on the car – do not "simplify" them away)

- **C++98 only** (QNX GCC 4.4 / GCC 4.6): no `auto`, lambdas, `nullptr`, `<cstdint>` features beyond C99 headers,
  range-for. No BMW headers exist: framework classes are declared by hand in `engine_data.cpp` with exact parameter
  types so the mangled names match the cars' exports. Every new `bmw::` symbol must be checked with `nm -D` in **both**
  `lib/` folders before use.
- **Pictures are sent as data**, not from the image DB: a large image DB made the EntryNav2 HMI show no images at all
  (onError 9). Frames live in `GaugeApp_frames*.bin` (`"GFR1"`, u32 count, sorted `(id, offset, size)` table, PNGs,
  little endian) and are sent with `PluginApp::updateModel(model, bmw::Image)` into `raImageModel`s. `bmw::Image` has no
  exported destructor: its two members are destroyed by hand (see `sendImageData`).
- **~60 images per HMI state**: images beyond that stay empty. Each screen is its own state with its own budget
  (states: engine 10 = 47, Driving 14 = 19, Fuel 15 = 44, Performance 16 = 11, Warm-up 17 = 30; settings 12).
  Prefer one picture per whole number over digit-by-digit. A new screen: `SCREEN_*` lists + `SCREENS` in `make_db.py`,
  a `compute*` in `screens_view.hpp`, a case in `renderScreen` and its titles in `screenForTitle` (`engine_data.cpp`).
- Visible area ≈ 1250×470 px; the 960×400 design is scaled by `SCALE` 1.15 and placed at `ORIGIN`. ~5 updates/s is fine;
  only changed slots are sent.
- Texts in the text DB must stay **ASCII** (Polish without diacritics); texts drawn into pictures may use diacritics.
- XML ids (models, components, actions, states) must be globally unique; screen k uses models `1000k+99` (background)
  and `1000k+100+i`, components `1000k+299`/`1000k+300+i`; OPTION buttons 600+.
- Menu placement: `applicationType="OnlineServices"` = ConnectedDrive (car-verified; `"Online"` does not work).
- Frame pack size matters (flash space, `kFramesMax` 16 MB per pack). Every frame is an indexed PNG
  (`palette_colors`: 32 colours for text, 256 for the rest) - car-verified on the EntryNav2; package ~12 MB.

## CDS facts (EntryNav2 F40)

- Values arrive as UTF-16 JSON text; parse with `numField` / `strField`. Invalid → the `has*` flag goes false.
- `driving.gear`: 1 N, 2 R, 3 P, 4 = D, 5..12 = D1..D8 (gearbox gear + 4); 15 transient.
- `driving.acceleration`: m/s², `longitudinal` 65535 only in the first reading.
- `engine.consumption`: a growing counter, `%hu` (wraps at 65536), unit undocumented (1 µl/step assumed, calibrated
  from tank level, `fuel-cal.txt`). No boost pressure exists in CDS.
- `hmi.graphicalContext.menuTitle` = title of the state on screen; used to render only the visible screen
  (`g_visible`: one of ours / something else = nothing / unknown or an unknown plugin state with `appType` "4" = all).
- `engine.temperature` right after a start can be `{"engine":68,"oil":0}`: oil 0 next to coolant > 30 = no data.
- Frame packs are `mmap`ed read-only (`loadPack`), never copied into memory; `GaugeApp_frames_s.bin` is mapped on first
  use (`loadScreens`). Re-installing the files while the HMI runs needs a reboot.
- `vehicle.language` 18 = Polish (pictures switch Polish/English by it). Decimal numbers always use the comma
  (`kDecimalComma`): the decimal-point number sets are not generated (their ids + stride stay reserved).
- The full registry of the car's CDS names and JSON formats is in `libhmiremoting.so` on the car; the separate
  diagnostic app `../HU_Tools/CdsScan` subscribes to all of them and writes `cds-scan.txt`.

## Runtime files (data dir: EntryNav2 `/var/local/data/GaugeApp`, NBT `/var/opt/gaugeapp`)

`settings.txt` (kept; also `screen=`, the screen shown last: the entry button, raAction 6, opens it with focusEvent
90 + screen), `max.txt` (last run's maxima; maxima reset at every start), `torque-env.txt` and `fuel-cal.txt`
(kept, learned), `gauge-app.log` (EntryNav2, 512 KB rotated), `app-guard` (crash guard: 3 HMI restarts within 120 s
disable the app), `app.disable` (off switch). A `gauge-app.log` file on a USB stick turns on logging there.

## Working rules

- Change the look only in `make_db.py`, then regenerate; keep `src/gauge_ids.hpp` and the generated files in sync in
  the same change. Look at `res/preview*.png` after regenerating.
- Keep logic in the pure headers (`cds_values`, `drive_stats`, `*_view`) and cover it in `tests/test_cds_values.cpp`;
  lifecycle behaviour goes in `tests/app_host_test.cpp`. Update the fake framework when declaring new `bmw::` calls.
- New CDS property: add to `enum Prop` + `propName` + `apply` + `propValid`, extend `kStubs` in `engine_data.cpp`.
- Nothing in this repo has been confirmed on NBT Evo hardware; EntryNav2 behaviour is what the car showed. Say which
  parts are untested when reporting.
- Update README_PL.md (full) / README.md (short) and `docs/` when install steps, files or sizes change.
- Never commit BMW libraries, firmware dumps, car logs or `cds-scan.txt` (personal data: contacts, GPS, VIN).
- License: PolyForm Noncommercial 1.0.0 (patterns from NbtAad / entry-aad).
