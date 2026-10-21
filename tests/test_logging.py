"""Logging across process boundaries, without cameras.

Every check runs a scenario from logging_scenarios.py as a process of its
own, with child processes started by spawn, and reads what it writes.
Takes seconds.
"""

import re
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path

TESTS_DIR = Path(__file__).resolve().parent

# Longest time a scenario may take before the check gives up on it.
SCENARIO_TIMEOUT_S = 60

# One output line: time, level, process, name, message.
LINE_FORMAT = "{time:YYYY-MM-DD HH:mm:ss.SSSSSS}|{level}|{process.name}|{name}|{message}"
LINE = re.compile(r"^(\d{4}-\d\d-\d\d \d\d:\d\d:\d\d\.\d{6})\|(\w+)\|(\w+)\|([\w.]+)\|(.*)$")

# Configuration written for each scenario; WINDOW_MS is replaced. The
# translation applies to the logger lib and everything below it.
CONF_TEMPLATE = """
std_level = "INFO"
sort_window_ms = WINDOW_MS

[output.console]
enabled = true
colorize = false
format = "LINE_FORMAT"

[loggers.lib]
translate = { DEBUG = "TRACE", INFO = false }
""".replace("LINE_FORMAT", LINE_FORMAT)


def run_scenario(name: str, window_ms: int = 100):
    """Run one scenario; return its output and its exit code."""
    with tempfile.TemporaryDirectory() as tmp:
        conf = Path(tmp) / "logdruid.toml"
        conf.write_text(CONF_TEMPLATE.replace("WINDOW_MS", str(window_ms)))
        result = subprocess.run(
            [sys.executable, "-c",
             "import logging_scenarios; logging_scenarios.run()",
             name, str(conf)],
            cwd=TESTS_DIR, capture_output=True, text=True,
            timeout=SCENARIO_TIMEOUT_S)
    return result.stderr, result.returncode


def parsed(output: str):
    """The lines of the output that have the line format, as tuples."""
    return [match.groups() for match in map(LINE.match, output.splitlines())
            if match]


class MessagesTest(unittest.TestCase):
    """Messages of the main process and of its children arrive."""

    def test_main_and_children_arrive_with_process_and_module(self):
        output, code = run_scenario("talkers")
        self.assertEqual(code, 0, output)
        lines = parsed(output)
        alpha = [line for line in lines if line[2] == "alpha"]
        self.assertEqual(len(alpha), 20, output)
        self.assertEqual(len([line for line in lines if line[2] == "beta"]),
                         20, output)
        self.assertEqual(alpha[0][3], "logging_scenarios")
        self.assertIn(("INFO", "main", "main start"),
                      [(line[1], line[2], line[4]) for line in lines])

    def test_after_shutdown_the_main_process_writes_directly(self):
        output, code = run_scenario("talkers")
        self.assertEqual(code, 0, output)
        self.assertEqual(parsed(output)[-1][4], "after shutdown")


class OrderTest(unittest.TestCase):
    """The main process writes all messages ordered by time."""

    def test_time_stamps_rise_across_all_processes(self):
        output, code = run_scenario("talkers")
        self.assertEqual(code, 0, output)
        times = [line[0] for line in parsed(output)]
        self.assertEqual(times, sorted(times), output)

    def test_without_a_window_every_message_still_arrives(self):
        output, code = run_scenario("talkers", window_ms=0)
        self.assertEqual(code, 0, output)
        self.assertEqual(len(parsed(output)), 1 + 20 + 20 + 2, output)


class HardEndTest(unittest.TestCase):
    """A child killed while it logs blocks nobody (no shared lock across process boundaries)."""

    def test_the_survivor_logs_on_and_the_run_ends(self):
        output, code = run_scenario("killed")
        self.assertEqual(code, 0, output)
        lines = parsed(output)
        survivor = [line for line in lines if line[2] == "survivor"]
        self.assertEqual(len(survivor), 20, output)
        self.assertTrue(any(line[2] == "victim" for line in lines))
        self.assertEqual(lines[-1][4], "after shutdown")


class StdLoggingTest(unittest.TestCase):
    """Records of the standard logging module are taken over."""

    def setUp(self):
        output, code = run_scenario("std_logging")
        self.assertEqual(code, 0, output)
        self.messages = {(line[1], line[3], line[4])
                         for line in parsed(output)}

    def test_the_logger_name_becomes_the_name(self):
        self.assertIn(("WARNING", "lib.sub", "lib warning"), self.messages)

    def test_a_level_translated_below_the_threshold_is_hidden(self):
        self.assertNotIn("lib debug", {message for *_, message in
                                       self.messages})

    def test_a_level_translated_to_false_is_dropped(self):
        self.assertNotIn("lib info", {message for *_, message in
                                      self.messages})

    def test_a_logger_without_translation_keeps_its_level(self):
        self.assertIn(("INFO", "other", "other info"), self.messages)


class ExceptionTest(unittest.TestCase):
    """A traceback travels as text through the pipe."""

    def test_the_traceback_appears_once(self):
        output, code = run_scenario("exception")
        self.assertEqual(code, 0, output)
        self.assertEqual(output.count("ZeroDivisionError: scenario failure"),
                         1, output)


if __name__ == "__main__":
    unittest.main()
