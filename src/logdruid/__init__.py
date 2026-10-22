"""A logging setup layer for multi-process applications, built on loguru.

Reporting uses loguru's own logger unchanged. logdruid sets it up and adds
one time-ordered output for all processes, the takeover of the standard
``logging`` module, and a configuration file of its own.

Documentation: https://fherb2.github.io/logdruid/
"""

from .logdruid import (
    CONFIG_FILE_NAME,
    LogLink,
    attach,
    check_config,
    link,
    logger,
    setup,
    shutdown,
)

__all__ = ["logger", "setup", "check_config", "link", "attach", "shutdown",
           "LogLink", "CONFIG_FILE_NAME"]
