"""Scenarios for test_logging.py, each run in a process of its own.

Not a test module itself -- the name carries no `test_` prefix, so
discovery passes it by. test_logging.py starts a scenario with

    python -c "import logging_scenarios; logging_scenarios.run()" NAME CONF

so that setup() changes the logging of that process only, and so that the
child processes find their functions under this module's name. All output
goes through logdruid to stderr in the format the test writes into CONF.
"""

import logging
import multiprocessing as mp
import os
import signal
import sys
import threading
import time
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent / "src"))

import logdruid                      # noqa: E402
from logdruid import logger          # noqa: E402

# Messages each talking child writes, and the pause between two of them.
MESSAGE_COUNT = 20
PAUSE_S = 0.007

# How long the victim may talk before the main process kills it.
KILL_AFTER_S = 0.3


def talker(log_link, label: str, pause_s: float) -> None:
    """Write MESSAGE_COUNT numbered messages, one per pause."""
    logdruid.attach(log_link)
    for index in range(MESSAGE_COUNT):
        logger.info(f"{label} {index}")
        time.sleep(pause_s)


def chatterbox(log_link) -> None:
    """Write as fast as possible until killed."""
    logdruid.attach(log_link)
    index = 0
    while True:
        logger.info(f"victim {index}")
        index += 1


def library_user(log_link) -> None:
    """Log through the standard logging module, as a library would."""
    logdruid.attach(log_link)
    logging.getLogger("lib.sub").debug("lib debug")
    logging.getLogger("lib.sub").info("lib info")
    logging.getLogger("lib.sub").warning("lib warning")
    logging.getLogger("other").info("other info")


def field_reporter(log_link) -> None:
    """Report with bound values, one of which cannot be pickled."""
    logdruid.attach(log_link)
    logger.bind(user="child", lock=threading.Lock()).info("child fields")
    logger.opt(record=True).info("child elapsed {record[elapsed]}")


def failer(log_link) -> None:
    """Log one exception with its traceback."""
    logdruid.attach(log_link)
    try:
        raise ZeroDivisionError("scenario failure")
    except ZeroDivisionError:
        logger.exception("caught")


def _start(ctx, target, name, *args):
    """Start a child process with its logging link, as an application does."""
    log_link = logdruid.link(name)
    process = ctx.Process(target=target, args=(log_link, *args), name=name)
    process.start()
    log_link.release()
    return process


def run() -> None:
    """Run the scenario named on the command line."""
    scenario, conf_path = sys.argv[1], Path(sys.argv[2])
    logdruid.setup(conf_path)
    ctx = mp.get_context("spawn")
    children = []

    if scenario == "talkers":
        logger.info("main start")
        children = [_start(ctx, talker, "alpha", "alpha", PAUSE_S),
                    _start(ctx, talker, "beta", "beta", PAUSE_S * 1.3)]
    elif scenario == "killed":
        victim = _start(ctx, chatterbox, "victim")
        children = [victim, _start(ctx, talker, "survivor", "survivor",
                                   PAUSE_S)]
        time.sleep(KILL_AFTER_S)
        os.kill(victim.pid, signal.SIGKILL)
    elif scenario == "std_logging":
        children = [_start(ctx, library_user, "user")]
    elif scenario == "exception":
        children = [_start(ctx, failer, "failer")]
    elif scenario == "fields":
        logger.bind(user="main").info("main fields")
        children = [_start(ctx, field_reporter, "fields")]
    elif scenario == "quiet":
        pass                            # setup and shutdown only
    else:
        raise SystemExit(f"unknown scenario {scenario}")

    for child in children:
        child.join()
    logger.info("main done")
    logdruid.shutdown()
    logger.info("after shutdown")
