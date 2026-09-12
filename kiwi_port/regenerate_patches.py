#!/usr/bin/env python3
"""Regenerate feature patches from a modified Chromium worktree."""

from __future__ import annotations

import argparse
import hashlib
import json
from pathlib import Path
import subprocess

FEATURES = [
    {"id": "resources", "name": "Kiwi menu resources and localized labels", "patch": "010-resources.patch", "files": ["chrome/android/chrome_java_resources.gni", "chrome/android/java/res/values/kiwi_ui.xml", "chrome/android/java/res/values-ja/kiwi_ui.xml"]},
    {"id": "app-menu-actions", "name": "Extension rows and basic Night mode menu actions", "patch": "020-app-menu-actions.patch", "files": ["chrome/android/java/src/org/chromium/chrome/browser/ChromeTabbedActivity.java", "chrome/android/java/src/org/chromium/chrome/browser/tabbed_mode/TabbedAppMenuPropertiesDelegate.java", "chrome/browser/ui/android/toolbar/java/src/org/chromium/chrome/browser/toolbar/extensions/ExtensionsToolbarCoordinator.java", "chrome/browser/ui/android/toolbar/java/src/org/chromium/chrome/browser/toolbar/extensions/ExtensionsToolbarCoordinatorImpl.java"]},
    {"id": "menu-presentation", "name": "Compact menu presentation and bottom-menu disabling", "patch": "030-menu-presentation.patch", "files": ["chrome/browser/chrome_browser_field_trials.cc", "chrome/browser/flags/android/java/src/org/chromium/chrome/browser/flags/ChromeFeatureList.java", "chrome/browser/ui/android/appmenu/internal/java/src/org/chromium/chrome/browser/ui/appmenu/AppMenu.java", "components/browser_ui/styles/android/java/res/values/styles.xml"]},
    {"id": "preference-registry", "name": "Chromium 152 registry for Titanium shared preferences", "patch": "040-preference-registry.patch", "files": ["base/android/java/src/org/chromium/base/shared_preferences/SharedPrefsUtils.java", "base/android/java/src/org/chromium/base/shared_preferences/StrictPreferenceKeyChecker.java", "chrome/browser/preferences/android/java/src/org/chromium/chrome/browser/preferences/AllPreferenceKeyRegistries.java"]},
    {"id": "night-mode-presets", "name": "Six Kiwi Night mode presets on the Chromium 152 renderer path", "patch": "050-night-mode-presets.patch", "files": ["chrome/android/java/src/org/chromium/chrome/browser/init/ProcessInitializationHandler.java", "chrome/browser/ui/android/night_mode/BUILD.gn", "chrome/browser/ui/android/night_mode/java/res/values-ja/kiwi_night_mode.xml", "chrome/browser/ui/android/night_mode/java/res/values/kiwi_night_mode.xml", "chrome/browser/ui/android/night_mode/java/res/xml/theme_preferences.xml", "chrome/browser/ui/android/night_mode/java/src/org/chromium/chrome/browser/night_mode/settings/ThemeSettingsFragment.java", "third_party/blink/renderer/platform/graphics/dark_mode_color_filter.cc", "third_party/blink/renderer/platform/graphics/dark_mode_color_filter.h", "third_party/blink/renderer/platform/graphics/dark_mode_filter.cc", "third_party/blink/renderer/platform/graphics/dark_mode_settings.h", "third_party/blink/renderer/platform/graphics/dark_mode_settings_builder.cc", "third_party/blink/renderer/platform/graphics/dark_mode_settings_builder.h", "third_party/blink/renderer/platform/graphics/dark_mode_filter_test.cc"]},
]


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("source", type=Path, help="modified Chromium git worktree")
    parser.add_argument("--base", default="HEAD", help="unmodified base revision")
    parser.add_argument("--output", type=Path, default=Path(__file__).resolve().parent / "patches")
    args = parser.parse_args()
    source, output = args.source.resolve(), args.output.resolve()
    output.mkdir(parents=True, exist_ok=True)
    series = {"format": 1, "base": args.base, "features": []}
    for definition in FEATURES:
        completed = subprocess.run(["git", "-C", str(source), "diff", "--binary", "--full-index", args.base, "--", *definition["files"]], capture_output=True)
        if completed.returncode:
            raise RuntimeError(completed.stderr.decode(errors="replace"))
        if not completed.stdout:
            raise RuntimeError(f"feature has no changes: {definition['id']}")
        patch = output / definition["patch"]
        patch.write_bytes(completed.stdout)
        item = dict(definition)
        item["sha256"] = hashlib.sha256(completed.stdout).hexdigest()
        series["features"].append(item)
    (output / "series.json").write_text(json.dumps(series, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")
    print(f"Regenerated {len(FEATURES)} feature patches in {output}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
