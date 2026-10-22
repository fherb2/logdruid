# logdruid

A drop-in logging setup layer for multi-process applications, built on
[loguru](https://loguru.readthedocs.io/). This documentation describes
version 0.1.1.

## 1 What logdruid is for

loguru is a logging library for Python with exactly one global logger.
Messages are reported with `logger.info(...)`, `logger.warning(...)` and so
on; outputs – the console, a file or a function of your own – are attached
with `logger.add(...)`. Each output has a minimum level, a format given as a
template with fields such as `{time}`, `{level}`, `{name}` and `{message}`,
and optionally a filter.

In an application with several processes, loguru alone reaches its limits. A
process started with the `spawn` start method has its own global logger with
its own outputs. For all processes to write into one shared file, loguru
offers a shared queue (`enqueue=True`); writing to it takes a lock that spans
all processes on Linux. If a process is killed hard while holding that lock,
every later logging call in every process hangs. Moreover, messages from
libraries that report through the standard library's `logging` module do not
appear in loguru's outputs.

logdruid is a setup layer around loguru for exactly this case: applications –
not libraries – with several processes. It does not build a logging API of
its own: you keep reporting with loguru's logger, unchanged. logdruid only sets
it up and adds what loguru does not offer: one shared output for all
processes, ordered by time, without a lock across process boundaries; taking
over the messages from `logging`; and a configuration in a file of its own.

For an application with a single process, loguru alone is enough; several
threads in one process are no problem for loguru either. loguru is also enough
when each process may write to its own file and the order across processes
does not matter. Libraries should use neither loguru nor logdruid but report
through `logging`; the application that uses them takes over their messages
([section 6](libraries.md)).

| Feature | loguru alone | with logdruid |
| --- | --- | --- |
| Reporting with `logger.info(...)` etc., levels `TRACE` to `CRITICAL` including `SUCCESS` | yes | yes, the same logger and the same API |
| Console and file, rotation and retention of the file, format, colours | yes | yes, set in the configuration file |
| Exceptions with extended tracebacks, optionally with variable values | yes | yes; variable values are off by default |
| All processes write into one shared output | yes, through a shared queue with a lock across all processes | yes, through a pipe of its own per child process, without a shared lock |
| A process killed hard does not hold up the others | not guaranteed, see above | yes |
| Messages of all processes ordered by time | no, order of arrival | yes, with an adjustable time window |
| Minimum level per name of a message (module, logger) | yes, through a filter | yes |
| Minimum level per process | no | yes |
| Taking over messages from `logging` | only as a code example in loguru's documentation | yes, with the logger's name and with level translation per logger |
| Configuration from a file, precedence defaults < application < file < command line | no, only environment variables | yes |
| Mistakes in the configuration do not stop the application | no, an unknown level aborts with `ValueError` | yes, they only produce a warning |
| Extra fields from `bind()` and `contextualize()` in the output | yes | yes, from child processes as well |

## 2 Installation and requirements

```bash
pip install logdruid
```

logdruid needs Python 3.11 or later and brings loguru 0.7.3 or later as a
dependency.

logdruid is tested and released for child processes started with the `spawn`
start method (`multiprocessing.get_context("spawn")`). It is not tested with
`fork`; a release for it follows in a later version. It is tested on Linux
with Python 3.11, 3.12 and 3.13.

**Versions and stability.** Version numbers follow Semantic Versioning. The
releases before `0.1.0` are development releases (`0.1.0.devN`); until then
anything may still change, the interface as well as the format of the
configuration file. From `0.1.0` on, as long as the first number is `0`, a
new second number announces a change that existing applications have to
adapt to; a new third number breaks nothing. Which names belong to the
interface is listed at the top of the [API reference](api.md); every change
to it and to the file format is in the [changelog](changelog.md).

The following pages build on each other in the order of the navigation: each
one only assumes what the pages before it explain.
