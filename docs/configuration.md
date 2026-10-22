# 5 Configuration

## 5.1 Where the file is found

The configuration lives in a file of its own in TOML format, separate from
the rest of the application's configuration. The application passes its path
as the first parameter of `setup()`; a relative path is relative to the
working directory.

Without a path, logdruid looks for a file named `logdruid.toml` in the
directory of the application's entry point
(`sys.modules["__main__"].__file__`), not in the working directory. If the
application has no entry point as a file, as with `python -c`, logdruid looks
for nothing and warns. If the application is installed as a package and
started through an entry point (`[project.scripts]`), it passes the path
explicitly.

If the file is missing or cannot be read, logdruid warns and carries on with
what the application has passed and with its own defaults. Child processes
never search themselves; they get the resolved configuration with the
`LogLink`.

## 5.2 Structure

All keys are optional.

| Key | Meaning | Section |
| --- | --- | --- |
| `std_level` | minimum level for everything that has none of its own | [5.4](#54-minimum-levels-per-process-and-per-name) |
| `sort_window_ms` | time window of the ordering in milliseconds | [5.6](#56-ordering-by-time) |
| `[output.console]` | output to the console | [5.3](#53-outputs) |
| `[output.file]` | output to a file | [5.3](#53-outputs) |
| `[processes.<name>]` | minimum level for a process | [5.4](#54-minimum-levels-per-process-and-per-name) |
| `[loggers.<name>]` | minimum level for a name, plus a translation of levels | [5.4](#54-minimum-levels-per-process-and-per-name), [6](libraries.md) |

An unknown key produces a warning and is skipped.

## 5.3 Outputs

There are two outputs, the console (`stderr`) and a file, each with a table
of its own:

```toml
[output.console]
enabled = true
colorize = true
format = "<green>{time:YYYY-MM-DD HH:mm:ss.SSS}</green> | <level>{level: <8}</level> | <cyan>{process.name}</cyan> | <cyan>{name}</cyan>: <level>{message}</level>"

[output.file]
enabled = true
path = "app.log"
rotation = "10 MB"
retention = 5
format = "{time:YYYY-MM-DD HH:mm:ss.SSS} | {level: <8} | {process.name} | {name}: {message}"
```

Two keys belong to logdruid itself: `enabled` switches an output on or off,
`path` is the path of the file and applies only to `[output.file]`. All other
keys are passed unchanged to loguru's `logger.add()` and are written the way
loguru expects them (see loguru's API documentation):

- in both tables: `format`, `colorize`, `serialize`, `catch`, `backtrace`,
  `diagnose`;
- only in `[output.file]`, additionally: `rotation`, `retention`,
  `compression`, `delay`, `watch`, `mode`, `buffering`, `encoding`.

The keys `sink`, `level`, `filter`, `enqueue` and `context` are set by
logdruid itself or not allowed – `enqueue` because it would bring back the
shared lock. Such a key or an unknown one produces a warning and is skipped.

By default the console is on and the file is off. Without `format`, loguru's
default format applies. A relative path of the file is relative to the
working directory at start; loguru creates missing directories itself.

**Which fields the format can use.** It follows from
[section 3](how-it-works.md) what is correct in the output: `{time}`,
`{level}`, `{message}`, `{name}`, `{module}`, `{function}`, `{line}` and
`{process}` with name and id. The following fields are not correct at
present, not even for messages of the `main` process; this will be fixed in
an upcoming version:

- `{extra}` is always empty; values from `bind()` and `contextualize()` are
  missing. A format with `{extra[key]}` makes every message disappear; loguru
  then writes "Logging error in Loguru Handler" to `stderr` instead.
- `{file}` always names logdruid's own file, not that of the message.
- `{thread}` names the thread that writes the message, so not reliably the
  one in which it was reported.
- `{elapsed}` refers to the moment of writing in the `main` process, not to
  the message.

A traceback is part of the message text, that is, of `{message}`; an
explicit `{exception}` in the format stays empty. With `serialize = true`,
the JSON contains the same fields in the same state.

**`backtrace` and `diagnose`** are set per output in its table, but always
act on both outputs alike: `diagnose`, the display of variable values in a
traceback, is on as soon as one enabled output switches it on; `backtrace`
stays on unless all enabled outputs switch it off. The reason lies in
[section 3](how-it-works.md): the traceback becomes text once, in the
reporting process, for all outputs. It is clearest to set both the same in
both tables. By default `diagnose` is off, as loguru advises for production
because it can reveal data; `backtrace` is on.

**When an output cannot be created:** if the file is enabled but has no
`path`, logdruid switches it off with a warning. If no output is enabled, it
warns and writes to the console. If an output cannot be created, for example
because the path is not writable, it warns; if no output exists at all
afterwards, it writes to the console.

## 5.4 Minimum levels per process and per name

```toml
std_level = "INFO"

[processes.worker]
level = "DEBUG"

[loggers."myapp.camera"]
level = "TRACE"

[loggers.somelib]
level = "WARNING"
```

`std_level` is the minimum level for everything that has none of its own.

`[processes.<name>]` sets the minimum level for a process. The name is the one
the process carries in its messages: for a child process the name from
`link()` ([section 4.2](integration.md#42-preparing-a-child-process)), for the
`main` process `process_name` from `setup()`, by default `main`.

`[loggers.<name>]` sets the minimum level for a name of a message. For the
application's own code this is the module name, such as `myapp.camera`; for a
library it is the name of its logger. An entry applies to its name and
everything below it: `somelib` also applies to `somelib.server`. If several
entries match, the longest one wins. A name with a dot is written in quotes,
as `"myapp.camera"` above; without them, TOML would read
`[loggers.myapp.camera]` as a nested table, and logdruid would see an entry
for `myapp` with an unknown key `camera`.

Within the file, a message gets: the matching entry for its name, otherwise
the entry for its process, otherwise `std_level`. In the example above,
messages from `somelib` in the process `worker` therefore appear only from
`WARNING` on, although the process is set to `DEBUG`.

The levels are named as in loguru: `TRACE`, `DEBUG`, `INFO`, `SUCCESS`,
`WARNING`, `ERROR`, `CRITICAL`; upper and lower case do not matter. An
unknown name produces a warning, and the entry is skipped.

One more key in `[loggers.<name>]`, `translate`, only concerns libraries that
report through `logging`; [section 6](libraries.md) describes it.

## 5.5 Four layers

The values come from four layers, from bottom to top:

1. logdruid's defaults (table at the end of this section);
2. what the application passes to `setup()` as `defaults=` – a dictionary
   with the same structure as the file;
3. the file;
4. the values from the command line, which the application passes to
   `setup()` as `cli_level=` and `cli_log_file=`.

logdruid does not read the command line itself. The application parses its
own arguments and hands the two values on, whatever it calls them on its
command line:

```python
import argparse

parser = argparse.ArgumentParser()
parser.add_argument("--log-level")
parser.add_argument("--log-file")
args = parser.parse_args()

logdruid.setup(conf_path, defaults={"std_level": "INFO"},
               cli_level=args.log_level, cli_log_file=args.log_file)
```

`cli_level` is a level name and replaces every level of all layers below it.
`cli_log_file` is the path of the log file; it only takes effect if the file
is enabled in one of the layers, and does not enable it by itself. `None`
means "not given" for both.

How the layers combine depends on the kind of value:

- **Minimum levels:** for a message, the highest layer that says anything
  about it decides – a matching entry for its name, an entry for its process,
  or `std_level`. Because `std_level` applies to everything, a layer with
  `std_level` hides all levels of the layers below it. This is why
  `cli_level` replaces everything. And this is why levels the application
  passes through `defaults=` no longer take effect as soon as the file sets
  `std_level`; such levels then belong in the file.
- **Outputs:** the tables `[output.console]` and `[output.file]` are merged
  key by key. If the application sets a `format` in `defaults=` and the file
  only sets `enabled` and `path`, the application's format is kept.
- **Translations** ([section 6](libraries.md)): the translation from the
  highest layer that has one for the name applies. Levels and translations
  are looked up separately; a `std_level` in the file does not hide
  translations from `defaults=`.
- **`sort_window_ms`:** the value of the highest layer that sets it applies.

logdruid's defaults:

| Value | Default |
| --- | --- |
| `std_level` | `INFO` |
| `sort_window_ms` | `100` |
| `[output.console]` | on, `diagnose = false`, loguru's format |
| `[output.file]` | off, `diagnose = false` |
| `backtrace` | on |

## 5.6 Ordering by time

`sort_window_ms` is the time window from [section 3](how-it-works.md), in
milliseconds. A larger window still orders correctly when the `main` process
reads a pipe late, but writes every message correspondingly later. `0`
switches the ordering off; messages then appear in the order in which they
arrive. A value that is not a number of 0 or more produces a warning and
switches the ordering off.

## 5.7 Mistakes in the configuration

A mistake in the configuration never stops the application. logdruid skips
the faulty value, works with the rest and reports each mistake as a warning
as soon as an output exists. Only valid values reach loguru.

Warnings arise for: a missing, unreadable or faulty file, an unknown key, an
unknown level name, an unknown or disallowed key of an output, a file output
without `path`, no enabled output, an output that cannot be created, an
invalid `sort_window_ms`, and an invalid translation
([section 6](libraries.md)).

**How to recognise logdruid's warnings.** They are on level `WARNING` under
the name `logdruid` (the `{name}` field in the format) and carry the process
name of the `main` process. The minimum levels from
[section 5.4](#54-minimum-levels-per-process-and-per-name) and
[5.5](#55-four-layers) do not apply to them: they appear with
`std_level = "ERROR"`, with `cli_level`, or with a `[loggers.logdruid]`
entry, in every enabled output. They are written at once, without the time
window from [section 3](how-it-works.md). The same holds for the warnings
logdruid issues about the transport while running
([section 4.5](integration.md#45-shutting-down) and
[7.4](exceptions.md#74-an-interrupted-transfer)).

## 5.8 A complete file

```toml
# Minimum level for everything without a level of its own.
std_level = "INFO"

# Time window of the ordering by time; 0 switches the ordering off.
sort_window_ms = 100

[output.console]
enabled = true
# Colours off when the output goes into a file or another program.
colorize = true
format = "<green>{time:YYYY-MM-DD HH:mm:ss.SSS}</green> | <level>{level: <8}</level> | <cyan>{process.name}</cyan> | <cyan>{name}</cyan>: <level>{message}</level>"
diagnose = false

[output.file]
enabled = true
# Relative to the working directory at start.
path = "app.log"
rotation = "10 MB"
retention = 5
format = "{time:YYYY-MM-DD HH:mm:ss.SSS} | {level: <8} | {process.name} | {name}: {message}"
diagnose = false

# One process with finer detail than the rest.
[processes.worker]
level = "TRACE"

# A library whose DEBUG is lasting fine detail (section 6).
[loggers.somelib]
translate = { DEBUG = "TRACE" }
```

A version with more comments is in the repository at
[`examples/logdruid.toml`](https://github.com/fherb2/logdruid/blob/main/examples/logdruid.toml).

## 5.9 Checking a configuration

Whether a configuration is free of mistakes can be checked without setting
anything up, for example in a test of the application or in its CI:

```python
import unittest
from pathlib import Path

import logdruid


class LoggingConfigTest(unittest.TestCase):

    def test_the_shipped_configuration_has_no_mistakes(self):
        path = Path(__file__).parent.parent / "myapp" / "logdruid.toml"
        self.assertEqual(logdruid.check_config(path), [])
```

`logdruid.check_config()` takes the same configuration parameters as
`setup()` – `config_path`, `defaults`, `cli_level`, `cli_log_file` – and
resolves the same four layers ([section 5.5](#55-four-layers)). It returns
the list of warnings `setup()` would report, empty for a configuration
without mistakes. It creates no output and changes nothing on the logger.
That is why it cannot tell whether an output can actually be created, for
example whether the path of the log file is writable; only `setup()` shows
that.
