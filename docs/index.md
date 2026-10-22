# logdruid

A drop-in logging setup layer for multi-process applications, built on
[loguru](https://loguru.readthedocs.io/).

logdruid does not replace loguru's API — it uses it unchanged — and adds
what a multi-process application needs on top: a single, time-ordered
output across process boundaries, without a lock shared between
processes, and the ability to take over messages from libraries that
report through the standard `logging` module.

## Installation

```bash
pip install logdruid
```

Requires Python 3.11 or later.

## Usage

Main process, once, before any child process is created:

```python
import logdruid
from logdruid import logger

logdruid.setup(config_path, cli_level=args.log_level)
logger.success("Logging active")
```

Per child process, in the main process:

```python
link = logdruid.link("worker")
process = ctx.Process(target=worker, args=(link, ...),
                       name="worker")
process.start()
link.release()
```

First thing in the child process (after ignoring `SIGINT`):

```python
logdruid.attach(link)
```

At the end of the main process, after the children have ended:

```python
logdruid.shutdown()
```

Application modules report through `from logdruid import logger` — loguru's
own global logger, unchanged. Libraries that report through the standard
`logging` module need no changes of their own; logdruid takes over their
messages and applies the level translations configured for them.

See [Configuration](configuration.md) for the `logdruid.toml` format, and
the [API reference](api.md) for every public function and class.

## License

MIT, see [`LICENSE`](https://github.com/fherb2/logdruid/blob/main/LICENSE)
in the repository.
