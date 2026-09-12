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
- Verify high contrast for text roles; current adjustment is reached for
  selections and does not establish the requested text behavior.
- The lifetime Java dependency was verified against pinned Chromium and fixed
  to //chrome/browser/lifetime/android:java. Restart UX remains unvalidated.
- Replace string-presence tests with executed renderer/persistence tests.
- Finish settings, toolbar, tab work and whole-series upstream conflict tests.
- Select completed cache
  `kiwi-incremental-96e928eb318caecadebc48e07400e79aa4063ef9-stage-1`
  explicitly before dispatch; workflow still defaults to an older cache.

The local workspace has no out/Default. No remote cache mutation was performed.
The connector rejected cache-list GET; current cache availability is unverified.
The latest Actions run observed was successful run 34457042932, for the earlier
APK that the user reports crashes on startup, not these unbuilt changes.
