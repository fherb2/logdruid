"""Implementation of the logdruid package.

Public interface and usage: see the package docstring in
``logdruid/__init__.py``.
"""

import atexit
import copy
import heapq
import inspect
import itertools
import logging
import multiprocessing as mp
import sys
import threading
import time
import tomllib
from dataclasses import dataclass
from multiprocessing.connection import wait
from pathlib import Path
from typing import Any, Dict, List, Optional

from loguru import logger

# --- Module parameters ------------------------------------------------

CONFIG_FILE_NAME = "logdruid.toml"
"""Name of the configuration file setup() looks for next to the entry point."""

# Name under which logdruid writes its own warnings. They bypass the
# minimum levels: a level set too high must not hide a configuration error.
OWN_NAME = "logdruid"

# Lowest layer: what applies when neither API, file nor command line
# say anything. No translation, one level for everything.
MODULE_DEFAULTS: Dict[str, Any] = {
    "std_level": "INFO",
    "sort_window_ms": 100,
    "output": {
        "console": {"enabled": True, "diagnose": False},
        "file": {"enabled": False, "diagnose": False},
    },
}

# Keys of an output table that logdruid handles itself.
OWN_OUTPUT_KEYS = {"enabled", "path"}

# Parameters of loguru's add() that logdruid sets itself or forbids:
# level and filter come from the configuration, the sink from the table,
# and enqueue would bring back the shared lock.
RESERVED_OUTPUT_KEYS = {"sink", "level", "filter", "enqueue", "context"}

# Parameters loguru accepts for file sinks only (loguru API, add()).
FILE_SINK_KEYS = {"rotation", "retention", "compression", "delay", "watch",
                  "mode", "buffering", "encoding"}

# Format of the handlers that collect or send messages. loguru appends a
# newline and the formatted exception to every string format by itself,
# so the text carries the traceback, which cannot be sent as an object.
COLLECT_FORMAT = "{message}"

# Upper bound on reading the pipes to their end in shutdown(). They end
# by themselves once the children have ended; this only keeps a forgotten
# release() from hanging the exit.
SHUTDOWN_TIMEOUT_S = 5.0

# Longest wait for a pipe to become readable when no message is due. It
# bounds how late a newly linked pipe is watched.
COLLECT_POLL_S = 0.05

# --- Module state -----------------------------------------------------

# Resolved configuration of this process; set by setup() or attach().
_settings: Optional["Settings"] = None

# Threshold per (process, name), filled on first use.
_threshold_cache: Dict[tuple, int] = {}

# Main process only: the collector and the output logger it writes to.
_collector: Optional["_Collector"] = None
_output = None


@dataclass
class Settings:
    """Resolved configuration, small enough to go to a child process.

    Attributes
    ----------
    layers : list of dict
        One entry per layer, highest priority first. Each holds
        ``std_level`` (level number or None), ``processes`` (process
        name -> level number) and ``loggers`` (name -> dict with an
        optional ``level`` number and an optional ``translate`` mapping
        of level names to level names or False).
    sort_window_s : float
        Ordering window in seconds; 0 switches the ordering off.
    outputs : dict
        Enabled outputs ('console', 'file') with the keyword arguments
        for loguru's add(), the file path under 'path'.
    backtrace : bool
        Passed to the handlers that format exceptions where they arise.
    diagnose : bool
        Same, for the display of variable values in tracebacks.
    """

    layers: List[Dict[str, Any]]
    sort_window_s: float
    outputs: Dict[str, Dict[str, Any]]
    backtrace: bool
    diagnose: bool


@dataclass
class LogLink:
    """What a child process needs to log into the main process.

    Created by link() in the main process and handed to the child as an
    argument; the child passes it to attach(). Its fields are internal;
    only release() is part of the public interface.
    """

    process_name: str
    conn: Any
    settings: Settings

    def release(self) -> None:
        """Drop the main process's copy of the write end.

        Call right after the child process has started. Without it the
        pipe never reaches its end, and shutdown() waits for nothing.
        """
        self.conn.close()


# --- Public functions -------------------------------------------------

def setup(config_path: Optional[Path] = None, *,
          defaults: Optional[Dict[str, Any]] = None,
          cli_level: Optional[str] = None,
          cli_log_file: Optional[str] = None,
          process_name: str = "main") -> None:
    """Set up logging in the main process.

    Call once, before any child process is created. Problems in the
    configuration are reported as warnings once the output exists; they
    never stop the application.

    Parameters
    ----------
    config_path : Path, optional
        Configuration file. Without it, ``logdruid.toml`` is looked for
        next to the entry point of the application.
    defaults : dict, optional
        Settings of the application, laid over the module defaults and
        under the file; same layout as the file.
    cli_level : str, optional
        Level of everything, from the command line. Overrides every
        level of file and API; translations stay.
    cli_log_file : str, optional
        Log file from the command line. Takes effect only when the file
        output is enabled.
    process_name : str
        Name this process carries in its messages.
    """
    global _settings, _collector, _output

    mp.current_process().name = process_name
    warnings: List[str] = []
    _settings = _load_settings(config_path, defaults, cli_level, cli_log_file,
                               warnings)
    _threshold_cache.clear()

    logger.remove()
    _output = copy.deepcopy(logger)
    _add_outputs(_output, _settings, warnings)

    _collector = _Collector(_output, _settings.sort_window_s)
    _collector.start()
    logger.add(_collector.collect, level=_min_threshold(process_name),
               filter=_level_filter, format=COLLECT_FORMAT,
               backtrace=_settings.backtrace, diagnose=_settings.diagnose)
    _take_over_std_logging(process_name)
    atexit.register(shutdown)

    for text in warnings:
        _output.patch(_own_name).warning(text)


def check_config(config_path: Optional[Path] = None, *,
                 defaults: Optional[Dict[str, Any]] = None,
                 cli_level: Optional[str] = None,
                 cli_log_file: Optional[str] = None) -> List[str]:
    """Check a configuration without setting anything up.

    Resolves the same layers as setup() and returns the warnings setup()
    would report about them. Whether an output can actually be created,
    for example whether the path of the log file is writable, only setup()
    finds out.

    Parameters
    ----------
    config_path, defaults, cli_level, cli_log_file
        As for setup().

    Returns
    -------
    list of str
        The warnings; empty if the configuration is sound.
    """
    warnings: List[str] = []
    _load_settings(config_path, defaults, cli_level, cli_log_file, warnings)
    return warnings


def link(process_name: str) -> LogLink:
    """Prepare logging for one child process; main process only.

    Parameters
    ----------
    process_name : str
        Name the child process will carry.

    Returns
    -------
    LogLink
        To be handed to the child process as an argument.
    """
    if _collector is None:
        raise RuntimeError("logdruid.setup() has to come first")
    read_end, write_end = mp.get_context("spawn").Pipe(duplex=False)
    _collector.add_pipe(read_end, process_name)
    return LogLink(process_name, write_end, _settings)


def attach(log_link: LogLink) -> None:
    """Set up logging in a child process.

    Call first in the process function, after ignoring SIGINT. Replaces
    loguru's default output by a handler that writes into the pipe of
    this process, and takes over the standard ``logging`` module.

    Parameters
    ----------
    log_link : LogLink
        Handed over by the main process.
    """
    global _settings

    mp.current_process().name = log_link.process_name
    _settings = log_link.settings
    _threshold_cache.clear()
    logger.remove()
    logger.add(_PipeSink(log_link.conn),
               level=_min_threshold(log_link.process_name),
               filter=_level_filter, format=COLLECT_FORMAT,
               backtrace=_settings.backtrace, diagnose=_settings.diagnose)
    _take_over_std_logging(log_link.process_name)


def shutdown() -> None:
    """Write out everything and close the output; main process only.

    Call at the end, after the child processes have ended. Reads every
    pipe to its end, writes what is still held back, and from then on
    writes the main process's messages directly, unsorted. Safe to call
    more than once.
    """
    if _collector is None or not _collector.is_alive():
        return
    _collector.stop(SHUTDOWN_TIMEOUT_S)


# --- Configuration ----------------------------------------------------

def _load_settings(config_path: Optional[Path],
                   defaults: Optional[Dict[str, Any]],
                   cli_level: Optional[str],
                   cli_log_file: Optional[str],
                   warnings: List[str]) -> Settings:
    """Resolve the four layers into Settings, collecting the warnings."""
    file_layer = _read_config_file(config_path, warnings)
    cli_layer: Dict[str, Any] = {}
    if cli_level is not None:
        cli_layer["std_level"] = cli_level
    if cli_log_file is not None:
        cli_layer["output"] = {"file": {"path": cli_log_file}}
    raw_layers = [cli_layer, file_layer, defaults or {}, MODULE_DEFAULTS]
    return _resolve(raw_layers, warnings)


def _read_config_file(config_path: Optional[Path],
                      warnings: List[str]) -> Dict[str, Any]:
    """Return the file layer, or an empty one with a warning."""
    if config_path is None:
        main_file = getattr(sys.modules.get("__main__"), "__file__", None)
        if main_file is None:
            warnings.append(f"No entry point file, so no {CONFIG_FILE_NAME} "
                            f"is looked for; using API and defaults only")
            return {}
        config_path = Path(main_file).resolve().parent / CONFIG_FILE_NAME
    try:
        with open(config_path, "rb") as file:
            return tomllib.load(file)
    except FileNotFoundError:
        warnings.append(f"{config_path} not found; using API and defaults "
                        f"only")
    except (OSError, tomllib.TOMLDecodeError) as exc:
        warnings.append(f"{config_path} cannot be read ({exc}); using API "
                        f"and defaults only")
    return {}


def _resolve(raw_layers: List[Dict[str, Any]],
             warnings: List[str]) -> Settings:
    """Turn the raw layers, highest first, into Settings."""
    layers = [_resolve_levels(raw, warnings) for raw in raw_layers]

    window_ms = next((raw["sort_window_ms"] for raw in raw_layers
                      if "sort_window_ms" in raw), 0)
    if not isinstance(window_ms, (int, float)) or window_ms < 0:
        warnings.append(f"sort_window_ms must be a number >= 0, not "
                        f"{window_ms!r}; ordering switched off")
        window_ms = 0

    outputs: Dict[str, Dict[str, Any]] = {}
    for kind in ("console", "file"):
        merged: Dict[str, Any] = {}
        for raw in reversed(raw_layers):
            merged.update(raw.get("output", {}).get(kind, {}))
        if merged.pop("enabled", False):
            outputs[kind] = _checked_output(kind, merged, warnings)
    if "file" in outputs and not outputs["file"].get("path"):
        warnings.append("File output enabled without a path; switched off")
        del outputs["file"]
    if not outputs:
        warnings.append("No output enabled; writing to the console")
        outputs["console"] = {}

    backtrace = any(params.pop("backtrace", True)
                    for params in outputs.values())
    diagnose = any(params.pop("diagnose", False)
                   for params in outputs.values())
    return Settings(layers, window_ms / 1000, outputs, backtrace, diagnose)


def _resolve_levels(raw: Dict[str, Any],
                    warnings: List[str]) -> Dict[str, Any]:
    """Pick the levels and translations out of one raw layer."""
    known = {"std_level", "sort_window_ms", "output", "processes", "loggers"}
    for key in raw.keys() - known:
        warnings.append(f"Unknown logging setting '{key}' ignored")

    layer: Dict[str, Any] = {
        "std_level": _level_no(raw.get("std_level"), "std_level", warnings),
        "processes": {},
        "loggers": {},
    }
    for name, entry in raw.get("processes", {}).items():
        for key in entry.keys() - {"level"}:
            warnings.append(f"Unknown key '{key}' for process '{name}' "
                            f"ignored")
        level = _level_no(entry.get("level"), f"process '{name}'", warnings)
        if level is not None:
            layer["processes"][name] = level
    for name, entry in raw.get("loggers", {}).items():
        for key in entry.keys() - {"level", "translate"}:
            warnings.append(f"Unknown key '{key}' for logger '{name}' "
                            f"ignored")
        resolved: Dict[str, Any] = {}
        level = _level_no(entry.get("level"), f"logger '{name}'", warnings)
        if level is not None:
            resolved["level"] = level
        if "translate" in entry:
            resolved["translate"] = _checked_translation(
                name, entry["translate"], warnings)
        if resolved:
            layer["loggers"][name] = resolved
    return layer


def _level_no(level: Any, what: str, warnings: List[str]) -> Optional[int]:
    """Return the number of a level name, or None with a warning."""
    if level is None or level == "":
        return None
    try:
        return logger.level(str(level).upper()).no
    except ValueError:
        warnings.append(f"Unknown level '{level}' for {what} ignored")
        return None


def _checked_translation(name: str, translation: Any,
                         warnings: List[str]) -> Dict[str, Any]:
    """Keep the valid pairs of a translation: level name -> name or False."""
    checked: Dict[str, Any] = {}
    if not isinstance(translation, dict):
        warnings.append(f"translate of logger '{name}' must be a table; "
                        f"ignored")
        return checked
    for source, target in translation.items():
        if target is False:
            checked[source.upper()] = False
        elif _level_no(target, f"translation {source} of logger '{name}'",
                       warnings) is not None:
            checked[source.upper()] = str(target).upper()
    return checked


def _checked_output(kind: str, params: Dict[str, Any],
                    warnings: List[str]) -> Dict[str, Any]:
    """Keep the parameters loguru accepts for this kind of output."""
    allowed = set(inspect.signature(logger.add).parameters) - {"kwargs"}
    allowed -= RESERVED_OUTPUT_KEYS
    allowed |= OWN_OUTPUT_KEYS
    if kind == "file":
        allowed |= FILE_SINK_KEYS
    else:
        allowed -= {"path"}
    checked = {}
    for key, value in params.items():
        if key in allowed:
            checked[key] = value
        else:
            warnings.append(f"Parameter '{key}' of output '{kind}' ignored")
    return checked


def _add_outputs(output, settings: Settings, warnings: List[str]) -> None:
    """Create console and file handlers on the output logger."""
    created = 0
    for kind, params in settings.outputs.items():
        params = dict(params, backtrace=settings.backtrace,
                      diagnose=settings.diagnose)
        sink = params.pop("path") if kind == "file" else sys.stderr
        try:
            output.add(sink, level=0, **params)
            created += 1
        except (OSError, TypeError, ValueError) as exc:
            warnings.append(f"Output '{kind}' could not be created ({exc}); "
                            f"writing to the console")
    if not created:
        output.add(sys.stderr, level=0)


# --- Levels -----------------------------------------------------------

def _threshold(process: str, name: Optional[str]) -> int:
    """Level a message of this process and name must at least have."""
    key = (process, name)
    if key not in _threshold_cache:
        _threshold_cache[key] = _lookup_threshold(process, name or "")
    return _threshold_cache[key]


def _lookup_threshold(process: str, name: str) -> int:
    """Walk the layers, highest first; the first one with a value wins."""
    for layer in _settings.layers:
        entry = _longest_match(layer["loggers"], name, "level")
        if entry is not None:
            return entry
        if process in layer["processes"]:
            return layer["processes"][process]
        if layer["std_level"] is not None:
            return layer["std_level"]
    return 0


def _longest_match(entries: Dict[str, Dict[str, Any]], name: str,
                   field: str) -> Any:
    """Return the field of the entry for name or its nearest parent."""
    while True:
        if name in entries and field in entries[name]:
            return entries[name][field]
        if not name:
            return None
        cut = name.rfind(".")
        name = name[:cut] if cut != -1 else ""
        if not name:
            return None


def _min_threshold(process: str) -> int:
    """Lowest level any message of this process could pass with."""
    candidates = []
    for layer in _settings.layers:
        candidates += [entry["level"] for entry in layer["loggers"].values()
                       if "level" in entry]
        if process in layer["processes"]:
            candidates.append(layer["processes"][process])
            break
        if layer["std_level"] is not None:
            candidates.append(layer["std_level"])
            break
    return min(candidates, default=0)


def _level_filter(record: Dict[str, Any]) -> bool:
    """loguru filter: pass what reaches the threshold of its origin."""
    return record["level"].no >= _threshold(record["process"].name,
                                            record["name"])


def _translation(name: str) -> Dict[str, Any]:
    """Translation for a logger: from the highest layer that has one."""
    for layer in _settings.layers:
        found = _longest_match(layer["loggers"], name, "translate")
        if found is not None:
            return found
    return {}


# --- Taking over the standard logging module ----------------------------

class _InterceptHandler(logging.Handler):
    """Hands every record of ``logging`` to loguru (loguru's own recipe).

    The record keeps the logger name as its name, so that the entries
    per logger apply; its level is translated first.
    """

    def emit(self, record: logging.LogRecord) -> None:
        """Pass one record on, or drop it if its translation says so."""
        target = _translation(record.name).get(record.levelname,
                                               record.levelname)
        if target is False:
            return
        try:
            level = logger.level(target).name
        except ValueError:
            level = record.levelno

        # Find the caller outside of logging, so that {function} and
        # {line} point into the library that logged.
        frame, depth = inspect.currentframe(), 0
        while frame is not None and (depth == 0 or
                                     frame.f_code.co_filename == logging.__file__):
            frame = frame.f_back
            depth += 1

        logger.patch(lambda r: r.update(name=record.name)).opt(
            depth=depth, exception=record.exc_info).log(
            level, record.getMessage())


def _take_over_std_logging(process: str) -> None:
    """Route ``logging`` of this process into loguru."""
    lowest = _min_threshold(process)
    for layer in _settings.layers:
        for entry in layer["loggers"].values():
            for source, target in entry.get("translate", {}).items():
                if target is not False and logger.level(target).no >= lowest:
                    std_no = logging.getLevelName(source)
                    if isinstance(std_no, int):
                        lowest = min(lowest, std_no)
    logging.basicConfig(handlers=[_InterceptHandler()], level=lowest,
                        force=True)


# --- Transport between the processes ------------------------------------

def _own_name(record: Dict[str, Any]) -> None:
    """loguru patcher: mark a message as logdruid's own warning."""
    record.update(name=OWN_NAME)


def _to_item(message) -> Dict[str, Any]:
    """What travels for one message: its data, not loguru's objects."""
    record = message.record
    return {
        "time": record["time"],
        "level": record["level"].name,
        "process": record["process"].name,
        "pid": record["process"].id,
        "name": record["name"],
        "module": record["module"],
        "function": record["function"],
        "line": record["line"],
        "text": str(message).rstrip("\n"),
    }


class _PipeSink:
    """loguru sink of a child process: sends each message into its pipe.

    Only this process writes into the pipe, so no lock is shared with
    another process. loguru serialises the calls within the process.
    """

    def __init__(self, conn):
        self._conn = conn

    def __call__(self, message) -> None:
        self._conn.send(_to_item(message))


class _Collector(threading.Thread):
    """Main process: gathers all messages and writes them sorted by time.

    Watches the pipes of the children with multiprocessing.connection.
    wait(), takes the main process's own messages through collect(), and
    writes a message once it is older than the ordering window. A
    message that arrives later than that is written at once.
    """

    def __init__(self, output, window_s: float):
        super().__init__(name="logdruid-collector", daemon=True)
        self._output = output
        self._window_s = window_s
        self._pipes: Dict[Any, str] = {}
        self._heap: List[tuple] = []
        self._order = itertools.count()
        self._lock = threading.Lock()
        self._stopping = False

    def add_pipe(self, conn, process_name: str) -> None:
        """Watch the read end of a child's pipe from now on."""
        with self._lock:
            self._pipes[conn] = process_name

    def collect(self, message) -> None:
        """loguru sink of the main process: queue its own messages."""
        item = _to_item(message)
        if self.is_alive():
            self._push(item)
        else:
            self._write(item)

    def stop(self, timeout_s: float) -> None:
        """Read the pipes to their end, write everything, then return."""
        self._stopping = True
        self.join(timeout_s)
        if self.is_alive():
            self._output.patch(_own_name).warning(
                f"Logging pipes of {sorted(self._pipes.values())} did not "
                f"end within {timeout_s} s; their remaining messages are lost")
        with self._lock:
            self._flush(due_only=False)

    def run(self) -> None:
        """Read, order and write until stop() and the end of every pipe."""
        while True:
            with self._lock:
                pipes = list(self._pipes)
            if self._stopping and not pipes:
                break
            for conn in (wait(pipes, timeout=self._poll_time()) if pipes
                         else self._sleep()):
                self._read(conn)
            with self._lock:
                self._flush(due_only=True)
        with self._lock:
            self._flush(due_only=False)

    def _poll_time(self) -> float:
        """How long to wait: until the next message is due, at most a bit."""
        with self._lock:
            if not self._heap:
                return COLLECT_POLL_S
            due = self._heap[0][0] + self._window_s - time.time()
        return max(0.0, min(due, COLLECT_POLL_S))

    def _sleep(self) -> list:
        """Wait a little when no pipe is open yet; return nothing to read."""
        time.sleep(COLLECT_POLL_S)
        return []

    def _read(self, conn) -> None:
        """Take one message from a pipe, or drop the pipe at its end."""
        try:
            item = conn.recv()
        except EOFError:
            self._drop(conn, None)
            return
        except Exception as exc:
            # A child killed while sending leaves half a message behind.
            self._drop(conn, exc)
            return
        self._push(item)

    def _drop(self, conn, exc: Optional[Exception]) -> None:
        """Stop watching a pipe; report it if it did not end cleanly."""
        with self._lock:
            name = self._pipes.pop(conn, "?")
        conn.close()
        if exc is not None:
            self._output.patch(_own_name).warning(
                f"Logging pipe of {name} broke off ({type(exc).__name__}); "
                f"later messages of that process are lost")

    def _push(self, item: Dict[str, Any]) -> None:
        """Queue a message by its time stamp."""
        with self._lock:
            heapq.heappush(self._heap, (item["time"].timestamp(),
                                        next(self._order), item))
        if self._window_s == 0:
            with self._lock:
                self._flush(due_only=False)

    def _flush(self, due_only: bool) -> None:
        """Write queued messages; with due_only those past the window.

        The caller holds the lock.
        """
        limit = time.time() - self._window_s
        while self._heap and (not due_only or self._heap[0][0] <= limit):
            _, _, item = heapq.heappop(self._heap)
            self._write(item)

    def _write(self, item: Dict[str, Any]) -> None:
        """Write one message with the data it arose with."""

        def restore(record):
            record.update(time=item["time"], name=item["name"],
                          module=item["module"], function=item["function"],
                          line=item["line"],
                          process=type(record["process"])(item["pid"],
                                                          item["process"]))

        self._output.patch(restore).log(item["level"], item["text"])
