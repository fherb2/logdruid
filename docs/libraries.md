# 6 Libraries that report through logging

In every process – with `setup()` in the `main` process, with `attach()` in a
child process – logdruid puts a handler at the root of `logging`. It hands
every message that arrives there on to loguru's logger:

- with the name of its logger as the name of the message, so that the
  `[loggers.<name>]` entries from
  [section 5.4](configuration.md#54-minimum-levels-per-process-and-per-name)
  apply to it;
- with its level after translation (below): with loguru's level of the same
  name, or, for a library's own level without one, with its number;
- with an attached exception and its traceback;
- with the caller in the library, so that `{module}`, `{function}` and
  `{line}` point into the library.

The rules of `logging` keep applying. logdruid **replaces all handlers at the
root** of `logging`; whatever the application put there before is gone
afterwards. Handlers on other loggers remain, and their messages additionally
reach logdruid as long as the logger propagates upwards – a library that
attaches a handler itself then appears twice. A logger with
`propagate = False` does not reach the root, and a level a library sets on
its own logger filters before. logdruid sets the level of the root to the
lowest level that can pass in the respective process, so that `logging` does
not create messages that would be discarded anyway.

**Translating levels.** A library does not know what the levels mean in the
application. What it reports on `DEBUG` is usually not temporary debugging
code in the sense of
[section 4.4](integration.md#44-reporting) but lasting fine detail, and some
libraries write one line per request on `INFO`. For this, `[loggers.<name>]`
has the key `translate`:

```toml
[loggers.somelib]
translate = { DEBUG = "TRACE" }

[loggers."somelib.access"]
translate = { INFO = "TRACE" }

[loggers.noisylib]
level = "WARNING"
translate = { INFO = false }
```

On the left is a level of the library, on the right the level it gets in the
application, or `false`, which discards the message. Like the level, a
translation applies to the name and everything below it; a name with a dot
is written in quotes here too
([section 5.4](configuration.md#54-minimum-levels-per-process-and-per-name)).
The level after translation is what gets compared with the minimum level: a
`DEBUG` message translated to `TRACE` only appears if `TRACE` is enabled for
its name and process. An unknown level name in a translation produces a
warning, and the pair is skipped; if `translate` is not a table, it is
skipped entirely with a warning. The translation only concerns messages from
`logging`, not the application's own messages through `logger`.

**Procedure when integrating a library.** Before a library goes into
operation, it pays to assess how it reports: from its documentation and, if it
consists of Python source, from that – which loggers it creates, on which
levels it reports, and how many messages arise per run, per request or per
event. From this come entries with `level` and `translate` where its levels do
not already match their meaning in the application. Finally, a run with
`std_level = "TRACE"` shows whether the number of messages per level fits,
especially on `INFO`; if not, the assignment is adjusted.
