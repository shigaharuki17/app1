import os
from pathlib import Path
import tempfile
import unittest
from unittest.mock import patch

from config import ConfigurationError, load_settings


class ConfigTest(unittest.TestCase):
    def test_key_file_and_secret_repr(self):
        with tempfile.TemporaryDirectory() as directory, patch.dict(os.environ, {}, clear=True):
            root = Path(directory)
            (root / "key.txt").write_text("unit-test-credential\n", encoding="utf-8")
            (root / ".env").write_text("DEEPSEEK_API_KEY_FILE=key.txt\n", encoding="utf-8")
            settings = load_settings(root)
            self.assertEqual(settings.api_key, "unit-test-credential")
            self.assertNotIn("unit-test-credential", repr(settings))

    def test_missing_configuration_has_actionable_error(self):
        with tempfile.TemporaryDirectory() as directory, patch.dict(os.environ, {}, clear=True):
            with self.assertRaisesRegex(ConfigurationError, "DEEPSEEK_API_KEY"):
                load_settings(Path(directory))

    def test_multiline_key_is_rejected_without_echo(self):
        with tempfile.TemporaryDirectory() as directory, patch.dict(os.environ, {}, clear=True):
            root = Path(directory)
            (root / "key.txt").write_text("private\nvalue", encoding="utf-8")
            (root / ".env").write_text("DEEPSEEK_API_KEY_FILE=key.txt", encoding="utf-8")
            with self.assertRaises(ConfigurationError) as caught:
                load_settings(root)
            self.assertNotIn("private", str(caught.exception))


if __name__ == "__main__":
    unittest.main()
