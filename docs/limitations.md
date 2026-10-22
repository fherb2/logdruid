# 8 Known limitations of this version

A summary of what the previous sections already state where it matters:

- Tested and released only for child processes started with the `spawn`
  start method; the release for `fork` follows in a later version
  ([section 2](index.md#2-installation-and-requirements)).
- Tested only on Linux, with Python 3.11 to 3.13
  ([section 2](index.md#2-installation-and-requirements)).
- Values from `bind()` and `contextualize()` as well as the fields `{extra}`,
  `{file}`, `{thread}` and `{elapsed}` do not arrive correctly in the output;
  a format with `{extra[...]}` makes messages disappear. To be fixed in an
  upcoming version ([section 5.3](configuration.md#53-outputs)).
- Uncaught exceptions do not go into the log but directly to `stderr`; for
  child processes there is a workaround with `logger.catch`. To be fixed in
  an upcoming version ([section 7.2](exceptions.md#72-uncaught-exceptions)).
- Only child processes of the `main` process can be attached, not processes
  a child process creates; a `LogLink` belongs to exactly one process
  ([section 4.2](integration.md#42-preparing-a-child-process)).
- `backtrace` and `diagnose` act on both outputs together
  ([section 5.3](configuration.md#53-outputs)).
