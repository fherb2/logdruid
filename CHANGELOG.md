# Changelog

All notable changes to logdruid are listed here. The format follows
[Keep a Changelog](https://keepachangelog.com/en/1.1.0/), and the version
numbers follow [Semantic Versioning](https://semver.org/). Until 0.1.0, the
development releases may still change anything; see "Versions and
stability" in the documentation.

## [0.1.0.dev3] - 2026-10-22

### Added

- `check_config()` checks a configuration without setting anything up and
  returns the warnings `setup()` would report, for tests and CI.
- Documentation: checking a configuration, versions and stability, and
  this changelog.
- Package metadata: project links (documentation, repository, issues,
  changelog) and classifiers for the tested Python versions.

### Changed

- logdruid's own warnings carry the name `logdruid` instead of the module
  path `logdruid.logdruid`, and no minimum level hides them any more.
- The README describes the project only; installation and usage are in
  the documentation.
- Package metadata names the author by GitHub account only.

### Removed

- `Settings` is no longer part of the public interface.

### Fixed

- Documentation: text in angle brackets that browsers swallowed; the API
  page no longer shows source code or a garbled usage example.

## [0.1.0.dev2] - 2026-10-22

### Changed

- The README points to the documentation website.
- Example configuration: remarks about command-line options removed;
  logdruid does not read the command line.

## [0.1.0.dev1] - 2026-10-22

### Added

- First release: a logging setup layer around loguru for multi-process
  applications. One time-ordered output in the main process, fed by a pipe
  per child process; takeover of the standard `logging` module with level
  translation per logger; minimum levels per process and per name; a
  configuration file with four layers.

[0.1.0.dev3]: https://github.com/fherb2/logdruid/releases/tag/v0.1.0.dev3
[0.1.0.dev2]: https://github.com/fherb2/logdruid/releases/tag/v0.1.0.dev2
[0.1.0.dev1]: https://github.com/fherb2/logdruid/releases/tag/v0.1.0.dev1
