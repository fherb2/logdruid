# 9 API reference

Generated from the docstrings. Everything here is also described in the
previous sections; this page is for looking things up.

The public interface consists of exactly the names on this page: `logger`,
`setup`, `check_config`, `link`, `attach`, `shutdown`, `LogLink` and
`CONFIG_FILE_NAME`. Of `LogLink`, only the type and `release()` are public.
Everything else is internal and may change without notice; what "notice"
means is described under "Versions and stability" in
[section 2](index.md#2-installation-and-requirements). Import from the
package: `import logdruid` or `from logdruid import logger, LogLink`.

`logdruid.logger` is loguru's global logger (`loguru.logger`), passed on
unchanged; its reporting API is described in
[loguru's documentation](https://loguru.readthedocs.io/en/stable/api/logger.html).
What should not be changed on it after the setup is described in
[section 4.4](integration.md#44-reporting).

::: logdruid
