# Configuration

Everything logdruid-specific lives in a `logdruid.toml` file, separate
from the rest of the application's configuration. Mistakes in it produce
a warning, never an abort — the application then runs with whatever
remains valid.

## Where the file is found

If no path is passed to [`setup()`][logdruid.setup], logdruid looks for
`logdruid.toml` next to the application's entry point
(`sys.modules["__main__"].__file__`), not the current working directory.
Child processes do not search themselves; the main process resolves the
configuration once and hands it over together with the logging link.

## The four layers

Values come from four layers, lowest first: logdruid's own defaults, what
the application passes to `setup()`, the file, and the command line. A
higher layer replaces a lower one field by field — a level set in the
file replaces a level from the API, but leaves that layer's translations
in place. On the command line, `std_level` is called `--log-level` and
replaces every level.

## Full example

```toml
--8<-- "examples/logdruid.toml"
```

## Levels, processes and names

Within one layer, the longest matching entry for a message's name wins —
an entry for `somelib` also applies to `somelib.server` — otherwise the
entry for its process, otherwise `std_level`. A logger can also have a
`translate` table: which of its own levels map to which level here, or
`false` to drop them entirely.

Suggested meaning of the levels (not enforced by logdruid itself):
`TRACE` is lasting fine detail of the regular code, `DEBUG` is reserved
for temporary debugging code, `INFO` is the regular course of operation,
`SUCCESS` marks a step that could have failed and did not. What a bundled
library reports on `DEBUG` is usually not debugging code in that sense,
but lasting fine detail — assign it a level when integrating the
library, typically `TRACE`.
