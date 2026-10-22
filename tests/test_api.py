"""The public interface of logdruid, as agreed (implementation doc 2.9).

A change to it is a decision, not a side effect: this check makes it
visible.
"""

import sys
import unittest
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent / "src"))

import logdruid  # noqa: E402

PUBLIC_NAMES = {"logger", "setup", "check_config", "link", "attach",
                "shutdown", "LogLink", "CONFIG_FILE_NAME"}


class PublicApiTest(unittest.TestCase):
    """__all__ lists exactly the public names, and each can be imported."""

    def test_all_lists_exactly_the_public_interface(self):
        self.assertEqual(set(logdruid.__all__), PUBLIC_NAMES)

    def test_every_public_name_is_importable(self):
        for name in PUBLIC_NAMES:
            self.assertTrue(hasattr(logdruid, name), name)


if __name__ == "__main__":
    unittest.main()
