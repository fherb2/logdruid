# 4 Integrating logdruid into an application

The integration has five places:

1. In the `main` process, once, before any child process is created:
   `logdruid.setup(...)`.
2. In the `main` process, per child process: `logdruid.link(...)` before the
   start, `release()` after it.
3. In the child process, as the first thing that has to do with logging:
   `logdruid.attach(...)`.
4. Everywhere: reporting with `from logdruid import logger`.
5. In the `main` process at the end, after all child processes have ended:
   `logdruid.shutdown()`.

## 4.1 Setting up in the main process

```python
import logdruid
from logdruid import logger

logdruid.setup()                      # or logdruid.setup(path_to_file)
logger.success("Logging active")
```

`setup()` is called once, in the `main` process, as early as possible and
before the first child process is created. Its first parameter is the path of
the configuration file; without it, logdruid looks for the file itself
([section 5.1](configuration.md#51-where-the-file-is-found)). Further optional
parameters are described in
[section 5.5](configuration.md#55-four-layers); `process_name` changes the
name of the `main` process in its messages, the default is `main`.

`setup()` does the following, in this order:

- It sets the name of the current process to `process_name`.
- It reads the configuration.
- It removes **all** previous outputs of loguru's global logger, including
  loguru's default output and any output the application added itself
  before.
- It creates the console and the file according to the configuration and
  starts the collecting thread.
- It takes over `logging`, replacing all handlers at the root of `logging`
  ([section 6](libraries.md)).
- It registers `shutdown()` with `atexit`
  ([section 4.5](#45-shutting-down)).
- Last, it reports problems in the configuration as warnings, as soon as an
  output exists
  ([section 5.7](configuration.md#57-mistakes-in-the-configuration)).

Whatever is reported before `setup()` still goes through loguru's default
output to `stderr`.

## 4.2 Preparing a child process

```python
import multiprocessing as mp

ctx = mp.get_context("spawn")
link = logdruid.link("worker")
process = ctx.Process(target=worker, args=(link, ...), name="worker")
process.start()
link.release()
```

`logdruid.link(name)` creates the pipe for one child process and returns a
`LogLink` object. It is called in the `main` process after `setup()`, once per
child process, before that process starts; without a previous `setup()` in the
same process it raises `RuntimeError`. The `LogLink` is handed to the child
process as an argument; it also carries the configuration the `main` process
has resolved, so the child process neither searches nor reads anything itself.

The name passed to `link()` is the name the child process carries in each of
its messages once it is attached ([section 4.3](#43-in-the-child-process)),
and the name its minimum level can be set by
([section 5.4](configuration.md#54-minimum-levels-per-process-and-per-name)).
The name `multiprocessing` assigns through `name=` only applies until then.
Choosing the same name for both is recommended.

`link.release()` belongs right after `process.start()`, not before it, because
`start()` still needs the `LogLink` to hand it over to the child process.
`release()` closes the copy of the write end that the `main` process still
holds. Without this call, the pipe does not end when the child process ends,
and `shutdown()` waits for it in vain at the end
([section 4.5](#45-shutting-down)).

`link()` only works in the `main` process. A child process cannot create a
connection of its own for a further process it creates. A `LogLink` belongs
to exactly one child process and must not be passed on to a second one,
because two processes would then write into the same pipe without a lock.

As a reminder from [section 2](index.md#2-installation-and-requirements):
this is tested only with child processes started with `spawn`.

## 4.3 In the child process

```python
import signal

import logdruid
from logdruid import logger


def worker(link, ...):
    signal.signal(signal.SIGINT, signal.SIG_IGN)   # the application's choice, see below
    logdruid.attach(link)
    logger.info("worker running")
    ...
```

`logdruid.attach(link)` attaches the child process. It sets the name of the
process to the name from the `LogLink`, removes loguru's default output in
this process, adds the handover into the pipe instead and takes over
`logging` in this process. A child process never creates an output of its
own.

`attach()` should be the first thing the child process does with logging.
Whatever it reports before that goes through loguru's default output directly
to `stderr`: unordered, in loguru's format and not into the file.

About ignoring `SIGINT` in the example: logdruid neither requires this nor
does it itself; it is a choice of the application, but one that suits
logdruid. Pressing Ctrl+C in a terminal sends `SIGINT` to all processes in
the foreground, the child processes included. Each child process would then
get a `KeyboardInterrupt` at an arbitrary point, possibly while writing a
message into its pipe. A half-written message makes the `main` process give
up that pipe; it then warns that later messages of this process are lost
([section 7.4](exceptions.md#74-an-interrupted-transfer)). Many applications
therefore let their child processes ignore `SIGINT` as the very first thing
and end them in an orderly way from the `main` process.

## 4.4 Reporting

Every module of the application reports through

```python
from logdruid import logger
```

This is loguru's global logger itself, not a copy and not a wrapper. Its
whole reporting API applies unchanged: `logger.trace()` to
`logger.critical()`, `logger.success()`, `logger.exception()`,
`logger.opt(...)` and so on. Importing it through logdruid instead of loguru
gives the same object; it keeps the link to the setup in one place.

What the application should not do after `setup()` or `attach()` is change
the logger's outputs itself: `logger.add()` would create an output that only
receives the messages of its own process and writes past the ordering by
time; `logger.remove()` and `logger.configure()` would cut the connection to
logdruid. Outputs belong in the configuration file
([section 5](configuration.md)).

`logger.bind()` and `logger.contextualize()` can be called without anything
failing, but the attached values do not reach the output at present, not
even for messages of the `main` process. A format that refers to such a field
with `{extra[...]}` makes the messages disappear entirely
([section 5.3](configuration.md#53-outputs)). This will be fixed in an
upcoming version.

Recommended meaning of the levels – logdruid does not enforce it, but it
helps when setting levels and when integrating libraries
([section 6](libraries.md)):

- `TRACE`: lasting fine detail of the regular code.
- `DEBUG`: reserved for temporary debugging code.
- `INFO`: the regular course of operation.
- `SUCCESS`: a step that could have failed and did not.
- `WARNING`: something unexpected; the work goes on as intended.
- `ERROR`: a function has failed; the work otherwise goes on.
- `CRITICAL`: this process cannot continue.

## 4.5 Shutting down

```python
for process in processes:
    process.join()
logdruid.shutdown()
logger.info("Application finished")
```

`logdruid.shutdown()` is called at the end in the `main` process, after all
child processes have ended. It reads every pipe to its end, writes everything
still held back and ends the collecting thread. From then on, the `main`
process writes its own messages directly, without a time window and without
ordering.

`shutdown()` waits at most 5 seconds for the pipes to end. If a child process
is still running then, or a `release()` was missing
([section 4.2](#42-preparing-a-child-process)), it warns with the names of
the processes concerned; their remaining messages are lost.

`shutdown()` may be called more than once. `setup()` has registered it with
`atexit`, so it also runs at the regular end of the interpreter if the
application forgets it. The explicit call after waiting for the child
processes remains the intended way: then all pipes are sure to have ended. If
the `main` process itself is killed hard, `atexit` does not run, and whatever
was held back in the time window is lost.

## 4.6 A complete example

```python
import multiprocessing as mp
import signal

import logdruid
from logdruid import logger


def worker(link, count):
    signal.signal(signal.SIGINT, signal.SIG_IGN)
    logdruid.attach(link)
    for step in range(count):
        logger.info(f"Step {step}")


def main():
    logdruid.setup()
    ctx = mp.get_context("spawn")
    link = logdruid.link("worker")
    process = ctx.Process(target=worker, args=(link, 3), name="worker")
    process.start()
    link.release()
    logger.info("Child process started")
    process.join()
    logdruid.shutdown()


if __name__ == "__main__":
    main()
```

If there is no `logdruid.toml` next to this script, logdruid warns once that
the file is missing and works with its defaults: output to the console
(`stderr`), minimum level `INFO`, time window 100 ms and loguru's default
format. That format does not show the name of the process;
[section 5.3](configuration.md#53-outputs) shows one that does.
