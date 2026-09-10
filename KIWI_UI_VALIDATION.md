# Validation record

Date: 2026-09-10

## Device result after the first complete build

- GitHub Actions run 34457042932 completed all 9,588 remaining Ninja edges and produced a signed APK.
- APK SHA-256: `9c8e7f1d3a56a6e70219cff24df52f98e928c492fc628fd602ffff58008579a9`.
- Device startup failed before UI validation. The direct cause was a null registry passed by
  `SharedPrefsUtils` into Chromium 152's `StrictPreferenceKeyChecker` while reading
  `close_tabs_on_exit`.
- The fix registers the Titanium keys in a real `PreferenceKeyRegistry`, adds that registry to
  `AllPreferenceKeyRegistries`, and removes the checker bypass. Assertions and strict checking stay enabled.
- The roughly 712 MiB APK and 470 MiB `libchrome.so` are properties of the current fast validation
  configuration (`is_debug=true`, non-official, no ThinLTO). Release optimization is a separate final
  output directory after functional work; it is not a reason to invalidate `out/Default`.

## Other startup log lines triaged separately

- `No parsed config found` comes from Vanadium's config parser. Its three no-config returns are an
  empty flag map, `null` component bytes, and version `-1`; this is a logged fallback, not the NPE path.
- `Environment.isMemoryDclRestricted` is a custom-OS reflection probe. Stock Android lacks the method;
  the wrapper caches the miss and returns nullable `Boolean`, and the inspected call sites test for
  `null` before use. It is noisy but not the startup crash.
- `libcrashpad_handler_trampoline.so` is deliberately omitted by Vanadium's `include_crashpad=false`
  GN path. The open error must be checked after the NPE fix, but re-enabling crashpad without matching
  packaging is not an accepted speculative fix.

## Incremental cache safety

- `out/Default` is never touched, removed, or overwritten during source timestamp reconciliation.
- Source provenance is stored in `out/Default/kiwi-source-state.json`; only changed patch-owned source
  files receive a new timestamp after the fresh tree is aged.
- A 100-input dependency simulation verifies that one edit exposes one stale edge and that the next
  checkpoint exposes zero already-completed edges.
- Before compilation, a Ninja dry-run must report work when the source plan contains changes. After
  compilation, `ChromePublic.apk` must be newer than the incremental build marker or publication fails.

## Passed locally

- Java parser accepted all 7 changed Java source files with Java 17 preview parsing.
- `git diff --check` accepted the source patch.
- `python3 -m py_compile kiwi_port/apply.py` passed.
- `python3 -m json.tool kiwi_port/manifest.json` passed.
- `bash -n build_kiwi_ui_arm64.sh` passed.
- A clean clone of the selected post-Titanium baseline accepted the patch.
- Every resulting file matched its manifest SHA-256.
- A second application reported an already-applied state without changing files.
- A deliberately modified baseline was rejected before applying the patch.

## Still required for the current change set

- GN generation
- Android Java type compilation
- Compilation and device startup with the registry fix and bundled UI work
- Six renderer-backed Night mode preset tests
- Patch regeneration and clean/upstream best-effort reapplication tests
- Final optimized release build in a separate output/cache namespace

The local workspace is used for patch and dependency tests. Full Chromium builds run in the
checkpointed GitHub workflow so the completed `out/Default` can be preserved between jobs.
