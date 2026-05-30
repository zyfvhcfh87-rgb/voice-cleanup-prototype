import json
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

from config import settings as settings_module
from config.settings import AppSettings, load_settings
from frontend.overlay_visibility import should_show_mic_overlay


class OverlayVisibilityTests(unittest.TestCase):
    def test_always_mode_shows_overlay_while_idle_and_active(self):
        self.assertTrue(should_show_mic_overlay("always", "idle"))
        self.assertTrue(should_show_mic_overlay("always", "recording"))

    def test_never_mode_hides_overlay_while_idle_and_active(self):
        self.assertFalse(should_show_mic_overlay("never", "idle"))
        self.assertFalse(should_show_mic_overlay("never", "recording"))

    def test_active_mode_hides_overlay_while_idle(self):
        self.assertFalse(should_show_mic_overlay("active", "idle"))

    def test_active_mode_shows_overlay_while_recording(self):
        self.assertTrue(should_show_mic_overlay("active", "recording"))

    def test_active_mode_shows_overlay_while_transcribing_or_processing(self):
        self.assertTrue(should_show_mic_overlay("active", "transcribing"))
        self.assertTrue(should_show_mic_overlay("active", "processing"))
        self.assertTrue(should_show_mic_overlay("active", "cleaning"))
        self.assertTrue(should_show_mic_overlay("active", "inserting"))


class OverlaySettingsMigrationTests(unittest.TestCase):
    def test_missing_overlay_setting_defaults_to_active(self):
        with tempfile.TemporaryDirectory() as temp_dir:
            settings_file = Path(temp_dir) / "settings.json"
            settings_file.write_text(
                json.dumps({"microphone_name": "Test Mic"}),
                encoding="utf-8",
            )

            with patch.object(settings_module, "SETTINGS_FILE", settings_file):
                loaded = load_settings()

        self.assertEqual(loaded.overlay_visibility_mode, "active")

    def test_old_enabled_overlay_setting_migrates_to_always(self):
        loaded = AppSettings(overlay_enabled=True)

        self.assertEqual(loaded.overlay_visibility_mode, "always")

    def test_old_disabled_overlay_setting_migrates_to_never(self):
        loaded = AppSettings(overlay_enabled=False)

        self.assertEqual(loaded.overlay_visibility_mode, "never")


if __name__ == "__main__":
    unittest.main()
