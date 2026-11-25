---
name: host-testing
description: How to test GaugeApp on the PC - pure logic tests and lifecycle tests against the fake BMW framework, in C++98 without a test framework. Use when adding logic, a CDS property, a setting, a screen, a framework call, or when a change needs proof before it goes to the car.
---

# Testing a car plugin on the PC

The car is the slowest and most expensive test environment (install, reboot, drive). Everything that can be decided
on the PC must be: parsing, units, maths, which frame each slot shows, what is written to disk, which framework calls
happen in which order. `make check` (in WSL) runs it all.

## Two layers

| Layer | File | What it covers |
|---|---|---|
| Pure logic | `tests/test_cds_values.cpp` | headers only (`cds_values`, `drive_stats`, `gauge_view`, `screens_view`): parse, compute, format |
| Lifecycle | `tests/app_host_test.cpp` + `fake_appframework.*` | the real `libGaugeApp.so` built for the host (NBT and EntryNav2 variants), driven through `pluginAppInfo` |

Put logic in the pure headers so it lands in the first layer: it is faster to test and needs no fake.

## Writing tests without a framework (C++98)

- Keep the tiny harness: `CHECK(cond)` prints `FAIL file:line: cond` and counts; `main` returns non-zero if anything
  failed. Use `CHECK_EQ(a, b)` (both test files) for integer comparisons: it prints `got 56130, want 56131`.
- One `static void testThing()` per behaviour, each starting from a fresh state (`Settings st;`, a new `Trip`). Tests
  must not depend on the order they run in.
- Name the case after the rule, and put the car fact next to it:
  `// F40: gear 5..12 = D1..D8 (gearbox gear + 4)`.
- Test the edges, not just the happy path: invalid JSON, `{"error":400}`, out-of-range values, counter wrap-around
  (65535 → 0), missing files, old file formats (a `settings.txt` without the newer keys), junk in files.
- Floating point: compare with a tolerance (`NEAR`), never `==`.
- Time: inject it (`now` in ms as a parameter, as `apply` and `Trip::tick` do); never read the clock inside logic.

## Lifecycle tests against the fake

- The fake implements every `bmw::` symbol the plugin declares and **records** what happens: models written,
  handlers registered, events triggered, Runnables posted. When the plugin declares a new call, the fake gets it in
  the same change.
- Drive the plugin as the car does: `create` → `onInit` → run posted Runnables (`runPosted()`) → feed CDS values
  (`feed(prop, json)`) → press actions (call the registered delegate) → `onError` / `onFinalize` → `onInit` again
  (restart) → `destroy`.
- Check effects, not internals: frame ids in models, file contents (`settings.txt`, `max.txt`), events fired, nothing
  posted after finalize.
- Point data and plugin folders into the build directory (`-DGAUGE_DATA_DIR=...`) and remove files a test depends on
  before it starts.
- Split the long scenario into named phases with their own setup (start, visibility, settings, entry button,
  restart), so the first failure tells you which behaviour broke.

## What the PC cannot prove (say so when reporting)

- The real framework's behaviour: whether the HMI accepts the XML, how many images a state shows, focus/back
  navigation, timing.
- Car data: units, signs and scales of CDS values (pedal, brake, steering sign, consumption).
- NBT Evo: no hardware test at all yet.

## Before finishing a change

- [ ] `make check` passes: `test_cds_values OK`, `app_host_test OK` twice (NBT, EntryNav2), crash guard OK.
- [ ] A new behaviour has at least one test that fails without the change.
- [ ] A new `bmw::` call is in the fake and checked in `app_host_test`.
- [ ] Report which parts are only PC-verified.

## Where GaugeApp differs today

- `app_host_test.cpp` runs named phases (onInit, subscription, engine values, language, fuel, screens, settings,
  entry button, restart) in order on one app: `create()` may run once per process (crash guard), so a phase starts
  from what the previous ones left. Failures print `[phase]`; `CHECK_EQ` prints both values. Independent phases
  would need `create()` per phase with the crash guard reset in between.
- The host test binary is built with `-std=gnu++11` (the fake uses `std::map`/`std::vector` conveniences), while the
  plugin under test is C++98; keep the plugin side C++98 regardless.
- `make_db.py` has no tests (see the `python-asset-generator` skill).
