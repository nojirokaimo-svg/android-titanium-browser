# Current implementation checkpoint

The existing Night mode feature patch is a work in progress, not a validated
six-mode implementation. Do not dispatch a full build from this checkpoint.

Completed in this continuation:

- Retained the existing preference registry crash fix and source provenance code.
- Compared the LAB formula with Kiwi commit
  `7be7edd1532148f22103cb4c5a1964d96297836f` and connected the contrast setting
  to the LAB lightness pivot (100 + contrast * 100), clamping L to [0, 100].
- Rejected nonfinite renderer settings before conversion to float.
- Disabled AndroidX persistence in XML so preference inflation cannot write
  an unregistered setting. Restart now requires successful synchronous storage.
- Preset selection no longer silently enables global website darkening.

Remaining before build:

- Fractional image grayscale is now implemented with SkColorMatrix saturation
  and cc::ColorFilter::MakeMatrix, following the old Kiwi image-filter path.
  Renderer execution tests are still required. No-settings defaults retain the
  Chromium LAB pivot of 110 and original image filter.
- High contrast is now connected to foreground/list-symbol PaintFlags using
  Chromium BlendForMinContrast, preserving author alpha. Three renderer C++
  regression tests were added to the existing dark_mode_filter_test.cc target.
  These tests have NOT been compiled/run; renderer validation remains required.
- The lifetime Java dependency was verified against pinned Chromium and fixed
  to //chrome/browser/lifetime/android:java. Presets save synchronously and expose
  an explicit restart action when the saved renderer switch differs from the
  running process. Invalid values/storage failure do not restart. Device UX and
  Java type checking remain unvalidated.
- Replace string-presence tests with executed renderer/persistence tests.
- Finish settings, toolbar, tab work and whole-series upstream conflict tests.
  Three disposable-git tests now pass for reapply idempotence, atomic strict
  rejection, and independent-feature application with named conflict reports.
  These are framework tests, not full Chromium upstream reapplication proof.
- Workflow now explicitly defaults to completed cache
  `kiwi-incremental-96e928eb318caecadebc48e07400e79aa4063ef9-stage-1`
  and requires restore. Confirm availability before compilation; never silently
  fall back to an older or empty cache.

The local workspace has no out/Default. No remote cache mutation was performed.
The connector rejected cache-list GET; current cache availability is unverified.
The latest Actions run observed was successful run 34457042932, for the earlier
APK that the user reports crashes on startup, not these unbuilt changes.
