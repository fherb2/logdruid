"""Fast checks of the logging configuration, no subprocess needed.

Run with either of:
    python3 -m unittest discover -s tests
    pytest tests/test_config.py
"""

import sys
import unittest
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent / "src"))

import logdruid.logdruid as logdruid  # noqa: E402  (whitebox: the impl module)


def _resolved(*layers):
    """Resolve the given layers, highest first, over logdruid's defaults."""
    warnings = []
    settings = logdruid._resolve(list(layers) + [logdruid.MODULE_DEFAULTS],
                                  warnings)
    return settings, warnings


def _no(level):
    """Number of a level name."""
    return logdruid.logger.level(level).no


class LoggingLayersTest(unittest.TestCase):
    """Levels per name and per process from four layers."""

    def use(self, *layers):
        """Make the resolved layers the settings of this process."""
        settings, warnings = _resolved(*layers)
        previous = logdruid._settings
        logdruid._settings = settings
        logdruid._threshold_cache.clear()

        def restore():
            logdruid._settings = previous
            logdruid._threshold_cache.clear()

        self.addCleanup(restore)
        return warnings

    def test_without_any_layer_the_module_default_applies(self):
        self.use()
        self.assertEqual(logdruid._threshold("p", "mod"), _no("INFO"))

    def test_std_level_fills_its_layer(self):
        self.use({"std_level": "WARNING"})
        self.assertEqual(logdruid._threshold("p", "mod"), _no("WARNING"))

    def test_the_longest_matching_name_wins(self):
        self.use({"std_level": "INFO",
                  "loggers": {"lib": {"level": "ERROR"},
                              "lib.sub": {"level": "TRACE"}}})
        self.assertEqual(logdruid._threshold("p", "lib.sub.x"), _no("TRACE"))
        self.assertEqual(logdruid._threshold("p", "lib.other"), _no("ERROR"))
        self.assertEqual(logdruid._threshold("p", "libx"), _no("INFO"))

    def test_name_before_process_before_std_level(self):
        self.use({"std_level": "INFO",
                  "processes": {"w": {"level": "DEBUG"}},
                  "loggers": {"lib": {"level": "ERROR"}}})
        self.assertEqual(logdruid._threshold("w", "lib.a"), _no("ERROR"))
        self.assertEqual(logdruid._threshold("w", "mod"), _no("DEBUG"))
        self.assertEqual(logdruid._threshold("v", "mod"), _no("INFO"))

    def test_within_a_layer_the_specific_entry_keeps_its_level(self):
        self.use({"loggers": {"somelib": {"level": "INFO"},
                              "somelib.server": {"level": "ERROR"}}})
        self.assertEqual(logdruid._threshold("p", "somelib.server"),
                         _no("ERROR"))
        self.assertEqual(logdruid._threshold("p", "somelib.stream.x"),
                         _no("INFO"))

    def test_a_higher_layer_replaces_specific_entries_below(self):
        file_layer = {"loggers": {"lib": {"level": "WARNING"}}}
        api_layer = {"loggers": {"lib.sub": {"level": "TRACE"}}}
        self.use(file_layer, api_layer)
        self.assertEqual(logdruid._threshold("p", "lib.sub"), _no("WARNING"))

    def test_a_lower_layer_applies_where_the_higher_says_nothing(self):
        self.use({"loggers": {"lib": {"level": "WARNING"}}},
                 {"std_level": "ERROR"})
        self.assertEqual(logdruid._threshold("p", "mod"), _no("ERROR"))

    def test_the_cli_level_replaces_every_level_and_keeps_translations(self):
        cli_layer = {"std_level": "ERROR"}
        file_layer = {"std_level": "INFO",
                      "processes": {"w": {"level": "TRACE"}},
                      "loggers": {"lib": {"level": "TRACE",
                                          "translate": {"DEBUG": "TRACE"}}}}
        self.use(cli_layer, file_layer)
        self.assertEqual(logdruid._threshold("w", "lib.x"), _no("ERROR"))
        self.assertEqual(logdruid._threshold("w", "mod"), _no("ERROR"))
        self.assertEqual(logdruid._translation("lib.x"), {"DEBUG": "TRACE"})

    def test_the_translation_comes_from_the_highest_layer_with_one(self):
        file_layer = {"loggers": {"lib": {"translate": {"INFO": "TRACE"}}}}
        api_layer = {"loggers": {"lib.sub": {"translate": {"INFO": False}}}}
        self.use(file_layer, api_layer)
        self.assertEqual(logdruid._translation("lib.sub.x"),
                         {"INFO": "TRACE"})
        self.assertEqual(logdruid._translation("other"), {})


class LoggingConfigWarningsTest(unittest.TestCase):
    """Mistakes in the logging configuration warn and never abort."""

    def test_an_unknown_level_warns_and_a_lower_layer_applies(self):
        settings, warnings = _resolved({"std_level": "LOUD"})
        self.assertTrue(any("LOUD" in text for text in warnings))
        self.assertIsNone(settings.layers[0]["std_level"])

    def test_an_unknown_key_warns(self):
        _, warnings = _resolved({"colour": 1})
        self.assertTrue(any("colour" in text for text in warnings))

    def test_an_unknown_output_parameter_warns_and_is_dropped(self):
        settings, warnings = _resolved(
            {"output": {"console": {"enabled": True, "colour": 1}}})
        self.assertTrue(any("colour" in text for text in warnings))
        self.assertNotIn("colour", settings.outputs["console"])

    def test_enqueue_is_refused(self):
        settings, warnings = _resolved(
            {"output": {"console": {"enabled": True, "enqueue": True}}})
        self.assertTrue(any("enqueue" in text for text in warnings))
        self.assertNotIn("enqueue", settings.outputs["console"])

    def test_a_file_output_without_a_path_is_switched_off(self):
        settings, warnings = _resolved({"output": {"file": {"enabled": True}}})
        self.assertTrue(warnings)
        self.assertNotIn("file", settings.outputs)

    def test_no_output_falls_back_to_the_console(self):
        settings, warnings = _resolved(
            {"output": {"console": {"enabled": False}}})
        self.assertTrue(warnings)
        self.assertEqual(list(settings.outputs), ["console"])

    def test_an_unknown_translation_target_warns(self):
        settings, warnings = _resolved(
            {"loggers": {"lib": {"translate": {"DEBUG": "NOPE"}}}})
        self.assertTrue(any("NOPE" in text for text in warnings))
        self.assertEqual(settings.layers[0]["loggers"]["lib"]["translate"], {})


