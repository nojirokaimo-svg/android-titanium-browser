# Current implementation checkpoint

The existing Night mode feature patch is a work in progress, not yet a validated
six-mode implementation. An incremental validation build is now authorized from
this checkpoint; never clean or fall back to an older/empty cache.

Completed in this continuation:

- Retained the existing preference registry crash fix and source provenance code.
- Compared the LAB formula with Kiwi commit
  `7be7edd1532148f22103cb4c5a1964d96297836f` and connected the contrast setting
  to the LAB lightness pivot (100 + contrast * 100), clamping L to [0, 100].
- Rejected nonfinite renderer settings before conversion to float.
- Disabled AndroidX persistence in XML so preference inflation cannot write
  an unregistered setting. Restart now requires successful synchronous storage.
- Preset selection no longer silently enables global website darkening.
- Pinned Chromium 152 APIs used by the restart and contrast paths were checked
  before starting the incremental validation build.

Validation/build work in progress:

- Fractional image grayscale is implemented with SkColorMatrix saturation and
  cc::ColorFilter::MakeMatrix, following the old Kiwi image-filter path. The
  incremental build must compile the renderer path before this is considered valid.
- High contrast is connected to foreground/list-symbol PaintFlags using Chromium
  BlendForMinContrast, preserving author alpha. Three renderer C++ regression
  tests were added; they remain unvalidated until the Chromium target compiles/runs.
- The lifetime Java dependency is //chrome/browser/lifetime/android:java. Presets
  save synchronously and expose an explicit restart action when the saved renderer
  switch differs from the running process. Invalid values/storage failure do not
  restart. Java type/lint validation is delegated to the incremental build gate.
- After compile errors are resolved, continue executed renderer/persistence tests,
  then settings/toolbar/tab work and whole-series upstream conflict tests. Do not
  redo completed work or substitute old tab modes with aliases to GRID.
- Workflow explicitly restores only completed cache
  `kiwi-incremental-96e928eb318caecadebc48e07400e79aa4063ef9-stage-1`
  and requires restore. A cache miss must stop before compilation.

The local workspace has no out/Default. No clean operation is permitted. The
incremental GitHub Actions run triggered by this checkpoint is the source of truth
for Java/lint/native compile errors before further implementation changes.

- Chromium 152 SkColorMatrix API was corrected to use an explicit 20-float row-major buffer; patch/manifest/series hashes were updated together.
- The original read-only incremental workflow is restored; resume compile validation from the completed checkpoint.
