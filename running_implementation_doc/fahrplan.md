# Fahrplan

## Noch offen

1. **GitHub Pages in den Repo-Settings aktivieren** (Settings → Pages →
   Source: „GitHub Actions") — ohne das läuft `docs.yml` ins Leere. Vom
   Entwickler per Hand zu erledigen, wie die Rulesets vorhin.

2. **Ersten Release-Tag setzen** (`v0.1.0.dev1`), Trusted Publisher ist
   registriert.

3. **Kritische Fehler samt Rückverfolgung erfassen**, nach Kapitel 1.4 der
   Implementierungsdoku: Anforderungen dort sind nur gesammelt, nicht
   geplant — erst planen (eigener Planungsschritt), dann implementieren,
   dann in der Anwenderdokumentation beschreiben, wie eine Nutzeranwendung
   das Merkmal einbaut. Ergebnis: Version `0.1.0.dev2`.

4. **Rückintegration in `Anwenderprojekt`:** `dortiges Logging-Modul`
   durch `pip install logdruid` (bzw. Eintrag in dessen
   Abhängigkeitsliste) ersetzen, alle `from Vorgängermodul import ...` auf
   `from logdruid import ...` umstellen, `Logging-Konfiguration` zu
   `logdruid.toml` umbenennen, Segment 2.23 und 3.3.9 dort durch
   Querverweis auf dieses Repository ersetzen. Eigener, später
   anzugehender Schritt — nicht Teil der aktuellen Arbeit hier.

## Erledigt

- GitHub-Repo `logdruid` angelegt (public, Rulesets für `main` und `v*`).
- Lokaler Clone unter `~/git/logdruid`.
- Übernahme von `Logging-Modul`, `Logging-Konfiguration`, `test_logging.py`,
  `logging_scenarios.py` sowie der Klassen `LoggingLayersTest` und
  `LoggingConfigWarningsTest` aus `dortige Testdatei`, umbenannt auf `logdruid`
  und von projektinternen Verweisen bereinigt.
- Implementierungsdoku (Segmente 1–3 in einer Datei) geschrieben.
- `src/logdruid/__init__.py` auf reinen Re-Export reduziert, Implementierung
  nach `src/logdruid/logdruid.py` verschoben; `tests/test_config.py` darauf
  angepasst.
- `.gitignore` angelegt (inkl. `.venv/`, `.tox/`).
- `pyproject.toml` (Poetry, PEP-621-`[project]`-Tabelle, `src`-Layout),
  `poetry.toml` (`virtualenvs.in-project = true`) und `tox.ini`
  (`py311`/`py312`/`py313`) angelegt; `requires-python` auf `>=3.11,<4.0`
  korrigiert (Poetrys Resolver verlangt eine Obergrenze, weil `loguru`
  selbst `<4.0` erklärt).
- Lizenz: MIT. `LICENSE`-Datei sowie `license`/`license-files` in
  `pyproject.toml` eingetragen.
- README.md geschrieben.
- Poetry 2.5.1 installiert (offizielles Installer-Skript, nutzerlokal unter
  `~/.local/share/pypoetry` / `~/.local/bin`, zuvor inspiziert).
- `poetry install` ausgeführt: Dev-venv unter `.venv/` angelegt, `loguru`
  installiert, Paket im Editable-Modus installiert.
- Testlauf verifiziert: alle 26 Tests (`test_logging.py`, `test_config.py`)
  grün im Poetry-venv.
- Commit-Modus für diese Sitzung geklärt: `direct` auf `main`.
- Erster Commit (`0dde9f3`), gepusht nach `origin/main`.
- Version auf `0.1.0.dev1` gesetzt (PEP 440, kanonisch — `0.1.0dev1` wäre
  äquivalent normalisiert worden).
- CI aufgesetzt: `.github/workflows/tests.yml` (Matrix `py311`–`py313`
  über `tox`/`tox-gh`) und `.github/workflows/release.yml` (Build, `twine
  check`, Veröffentlichung über PyPI Trusted Publishing bei `v*`-Tag,
  Environment `pypi`).
- `tox`/`tox-gh` als Poetry-`dev`-Gruppe eingetragen (`pyproject.toml`,
  `poetry.lock`), damit lokal und in der CI dieselbe Fassung läuft; CI
  nutzt jetzt `poetry install --only dev` statt eines rohen `pip install`.
  Lokal verifiziert: `poetry run tox -e py312` grün.
- Badges in README.md (PyPI-Version, Testlauf-Status).
- PyPI-Konto: 2FA aktiviert, Trusted Publisher als „pending publisher"
  registriert (`logdruid`, Owner `fherb2`, `release.yml`, Environment
  `pypi`) — vom Entwickler selbst ausgeführt.
- Neues Kapitel 1.4 in der Implementierungsdoku: Anforderungsskizze
  „kritische Fehler samt Rückverfolgung erfassen", aus der
  `Anwenderprojekt`-Sitzung
  entnommen. Ausdrücklich als Anlehnung markiert, keine Vorgabe.
- **Dokumentation: mkdocs gewählt**, trotz eines dabei gefundenen
  gravierenden Befunds: MkDocs 1.x ist faktisch unbetreut (seit 18
  Monaten kein Release, seit 2026-10-02 für externe Beiträge
  geschlossen), MkDocs 2.0 bricht mit dem gesamten Plugin-Ökosystem
  (inkl. `mkdocstrings`) ohne Migrationspfad, und der Nachfolger
  Zensical hat `mkdocstrings` noch nicht bestätigt unterstützt.
  Entscheidung: MkDocs unterhalb 2.0 anpinnen (`mkdocs-material` ≥9.7.5,
  erweiterte Pflege laut Material-Team bis 2027-05-05), später auf
  Zensical prüfen, wenn dessen `mkdocstrings`-Unterstützung reif ist.
  `pyproject.toml` (Gruppe `docs`), `mkdocs.yml`, `docs/index.md`,
  `docs/configuration.md` (bindet `examples/logdruid.toml` per Snippet
  ein), `docs/api.md` (mkdocstrings) angelegt; `.github/workflows/docs.yml`
  (Build + Deploy auf GitHub Pages über `actions/deploy-pages`).
  `site/` in `.gitignore`. Ein Versions-Bug (`mkdocstrings` vs.
  `mkdocstrings-python`) korrigiert, Build lokal verifiziert
  (`poetry run mkdocs build --strict`, alle drei Seiten geprüft).
