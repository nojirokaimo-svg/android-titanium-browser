import json
import unittest
from pathlib import Path


ROOT = Path(__file__).resolve().parent


class NightModePatchTest(unittest.TestCase):
    def test_registry_and_all_six_presets_are_present(self):
        registry = (ROOT / "patches/040-preference-registry.patch").read_text()
        self.assertIn('"titanium.night_mode_preset"', registry)
        self.assertIn("new int[] {0, 1, 2, 3, 4, 5}", registry)
        for preset in ("case 2", "case 3", "case 4", "case 5", "default"):
            self.assertIn(preset, registry)
        added_lines = "\n".join(line[1:] for line in registry.splitlines() if line.startswith("+"))
        self.assertNotIn("isKeyInUse(key)", added_lines)

    def test_chromium_152_renderer_path_is_used(self):
        patch = (ROOT / "patches/050-night-mode-presets.patch").read_text()
        self.assertIn('switches::kDarkModeSettings', patch)
        self.assertIn('"dark-mode-settings"', patch)
        self.assertIn("DarkModeColorFilter::Create(settings)", patch)
        self.assertNotIn("is_debug", patch)
        self.assertNotIn("ENABLE_ASSERTS, false", patch)

    def test_new_files_are_incremental_inputs(self):
        manifest = json.loads((ROOT / "manifest.json").read_text())
        series = json.loads((ROOT / "patches/series.json").read_text())
        feature = next(item for item in series["features"] if item["id"] == "night-mode-presets")
        for path in feature["files"]:
            self.assertIn(path, manifest["files"])


if __name__ == "__main__":
    unittest.main()
