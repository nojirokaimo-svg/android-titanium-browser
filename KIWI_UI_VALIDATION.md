# Validation record

Date: 2026-09-05

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

## Not yet run

- GN generation
- Android Java type compilation
- Full Chromium/Titanium compilation
- APK signature verification
- Android installation and UI/runtime tests

The local workspace has about 32 GB total storage. Chromium's Android build
documentation requires at least 100 GB free, so a full build was not started in
this workspace.
