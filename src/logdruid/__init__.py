"""Logging setup for multi-process applications: a setup layer around loguru.

Reporting uses loguru unchanged: `logger` is loguru's global logger.
This module only sets it up, and adds what loguru does not offer:

- One output in the main process. Console and file are created there
  only; every child process sends its messages through a pipe of its
  own. Unlike loguru's ``enqueue=True`` no lock is shared between
  processes, so a child that is killed hard blocks nobody but itself.
- Ordering by time. The main process holds messages back for a short
  window and writes them sorted by their time stamp, its own included.
- Taking over the standard ``logging`` module, with the logger name as
  the name of the message and with levels translated per logger.
- Levels per process and per name, configured in ``logdruid.toml`` in
  four layers: module defaults < API < file < command line.

Usage
-----
Main process, once, before any child process is created:

>>> import logdruid
>>> from logdruid import logger
>>> logdruid.setup(config_path, cli_level=args.log_level)
>>> logger.success("Logging active")

Per child process, in the main process:

>>> link = logdruid.link("worker")
>>> process = ctx.Process(target=worker, args=(link, ...),
...                       name="worker")
>>> process.start()
>>> link.release()

First thing in the child process (after ignoring SIGINT):

>>> logdruid.attach(link)

At the end of the main process, after the children have ended:

>>> logdruid.shutdown()

Configuration file (all keys optional)::

    std_level = "INFO"            # level of everything without its own
    sort_window_ms = 100          # 0 switches the ordering off

    [output.console]              # parameters of loguru's add(),
    enabled = true                # passed through; 'enabled' and
    format = "..."                # 'path' are logdruid's own
    diagnose = false

    [output.file]
    enabled = false
    path = "app.log"
    rotation = "10 MB"
    retention = 5

    [processes.worker]
    level = "DEBUG"

    [loggers.somelib]            # applies to somelib.* as well
    level = "INFO"
    translate = { DEBUG = "TRACE", INFO = false }   # false drops

Notes on further development
----------------------------
- An application started through a packaged entry point has no
  ``logdruid.toml`` next to ``__main__``; it passes the path instead.
- Exceptions travel through the pipe as text formatted in the child;
  ``backtrace`` and ``diagnose`` therefore act where a message arises.
"""


from .logdruid import (
    CONFIG_FILE_NAME,
    LogLink,
    Settings,
    attach,
    link,
    logger,
    setup,
    shutdown,
)

__all__ = ["logger", "setup", "link", "attach", "shutdown", "LogLink",
           "Settings", "CONFIG_FILE_NAME"]
