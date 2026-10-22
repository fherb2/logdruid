# 7 Exceptions and crashes

## 7.1 Reported exceptions

An exception the application reports itself – with `logger.exception(...)`
or with `logger.opt(exception=True).critical(...)` – becomes text together
with its traceback in the reporting process and goes through the pipe as
such; `backtrace` and `diagnose`
([section 5.3](configuration.md#53-outputs)) act there. The traceback
appears exactly once in the output. `logger.exception()` reports on `ERROR`;
for a message meaning that the process cannot continue,
`logger.opt(exception=True).critical(...)` is the way.

## 7.2 Uncaught exceptions

An exception nobody catches does not reach the logging at present – this is
a limitation of this version, which an upcoming version will remove:

- In the main thread, Python writes it to `stderr` through
  `sys.excepthook`, in other threads through `threading.excepthook`.
- In a child process, `multiprocessing` itself writes "Process <name>:" and
  the traceback directly to `stderr`: unordered, not in the output's format
  and not into the file.

For child processes, loguru already offers a workaround today: wrap the
process function with `logger.catch`.

```python
import sys


@logger.catch(level="CRITICAL", onerror=lambda _: sys.exit(1))
def worker(link, ...):
    signal.signal(signal.SIGINT, signal.SIG_IGN)
    logdruid.attach(link)
    ...
```

Tested with version 0.1.0.dev1, `spawn` and Linux: the exception appears with
its traceback as a `CRITICAL` message of the child process, in order, in the
output; the process ends with exit code 1, and `multiprocessing` writes
nothing extra to `stderr`. Without `onerror`, the exception is reported just
the same, but the process ends with exit code 0, and the `main` process
cannot tell that it failed. The text `logger.catch` puts in front names
`multiprocessing`'s `run` as the function, not the process function; the
parameter `message="..."` replaces it. An exception before `attach()` still
goes through loguru's default output to `stderr`.

In the `main` process, the application catches an exception it cannot
continue from with `try` and `except` itself and reports it with
`logger.opt(exception=True).critical(...)`.

## 7.3 A process dying hard

If a process is ended with `SIGKILL`, ended by the system's out-of-memory
killer, or crashes in native code, it cannot report anything any more.
Whatever it had written into its pipe until then arrives, and the other
processes keep reporting undisturbed; tested for `SIGKILL`. That and how a
child process ended is seen only by the `main` process, for example from
`process.exitcode` (negative if a signal ended it); it reports this itself.

## 7.4 An interrupted transfer

If a child process breaks off in the middle of writing a message, half a
message remains in the pipe. The `main` process then gives up this pipe and
warns "Logging pipe of <name> broke off (…); later messages of that process
are lost". The other pipes are not affected. One possible cause is `SIGINT`
from Ctrl+C ([section 4.3](integration.md#43-in-the-child-process)).
