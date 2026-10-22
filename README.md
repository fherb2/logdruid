# logdruid

[![PyPI version](https://img.shields.io/pypi/v/logdruid.svg)](https://pypi.org/project/logdruid/)
[![Tests](https://github.com/fherb2/logdruid/actions/workflows/tests.yml/badge.svg)](https://github.com/fherb2/logdruid/actions/workflows/tests.yml)

A drop-in logging setup layer for multi-process applications, built on
[loguru](https://loguru.readthedocs.io/).

**Installation, usage, configuration and API:
<https://fherb2.github.io/logdruid/>**

## What it is for

loguru is a logging library for Python with exactly one global logger. In an
application with several processes, loguru alone reaches its limits: each
process started with `spawn` has its own logger with its own outputs; a
shared output across processes goes through a queue whose lock spans all
processes, so a process killed hard while holding it can block logging
everywhere; and messages from libraries that report through the standard
`logging` module do not appear in loguru's outputs.

logdruid is a setup layer around loguru for exactly this case: applications
– not libraries – with several processes. It does not build a logging API of
its own: you keep reporting with loguru's logger, unchanged. logdruid only
sets it up and adds what loguru does not offer: one shared output for all
processes, ordered by time, without a lock across process boundaries; taking
over the messages from `logging`; and a configuration in a file of its own.

For an application with a single process, loguru alone is enough, as it is
when each process may write to its own file and the order across processes
does not matter. Libraries should use neither loguru nor logdruid but report
through `logging`.

## Features

| Feature | loguru alone | with logdruid |
| --- | --- | --- |
| Reporting with `logger.info(...)` etc., levels `TRACE` to `CRITICAL` including `SUCCESS` | yes | yes, the same logger and the same API |
| Console and file, rotation and retention of the file, format, colours | yes | yes, set in the configuration file |
| Exceptions with extended tracebacks, optionally with variable values | yes | yes |
| All processes write into one shared output | yes, through a shared queue with a lock across all processes | yes, through a pipe of its own per child process, without a shared lock |
| A process killed hard does not hold up the others | not guaranteed | yes |
| Messages of all processes ordered by time | no, order of arrival | yes, with an adjustable time window |
| Minimum level per name of a message (module, logger) | yes, through a filter | yes |
| Minimum level per process | no | yes |
| Taking over messages from `logging` | only as a code example in loguru's documentation | yes, with the logger's name and with level translation per logger |
| Configuration from a file, precedence defaults < application < file < command line | no, only environment variables | yes |
| Mistakes in the configuration do not stop the application | no | yes, they only produce a warning |

## For contributors

Design rules and rationale are in
[`running_implementation_doc/`](https://github.com/fherb2/logdruid/tree/main/running_implementation_doc)
(in German).

## License

MIT, see [`LICENSE`](https://github.com/fherb2/logdruid/blob/main/LICENSE).
