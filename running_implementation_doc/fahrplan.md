# Fahrplan

## Noch offen

1. **Rückintegration in `Anwenderprojekt`** — *läuft gerade in
   einer anderen Sitzung/Instanz dort, nicht hier.* Diese Sitzung wartet,
   bis dort Anpassungsbedarf an logdruid gemeldet wird. Dort:
   `dortiges Logging-Modul` durch `pip install logdruid` (bzw. Eintrag in
   dessen Abhängigkeitsliste) ersetzen, alle `from Vorgängermodul import ...`
   auf `from logdruid import ...` umstellen, `Logging-Konfiguration` zu
   `logdruid.toml` umbenennen, Segment 2.23 und 3.3.9 dort durch
   Querverweis auf dieses Repository ersetzen. Als Anleitung dient die
   deutsche Anwenderdoku `running_implementation_doc/anwenderdoku.md`.
   Dabei gefundene Unzulänglichkeiten werden hier (in logdruid) behoben.

2. **Danach: finale Version `0.1.0` veröffentlichen** (Tag + Release),
   sobald Schritt 1 sauber durchlief.

## Vorgemerkt für das nächste Release

- **Felder bei der Weitergabe nicht verlieren:** Über die Pipe gehen je
  Meldung nur Zeit, Stufe, Prozess, Name, Modul, Funktion, Zeile und Text
  (`_to_item`/`_write` in `logdruid.py`). Dadurch fehlt `{extra}` (Werte
  aus `bind()`/`contextualize()`), auch im `main`-Prozess; `{file}`,
  `{thread}` und `{elapsed}` stimmen nicht; ein Format mit
  `{extra[...]}` lässt Meldungen verschwinden (am 2026-10-22 beobachtet).
  Die Anwenderdoku (5.3, 8) beschreibt das als Grenze und kündigt die
  Behebung an; nach der Behebung dort anpassen.
- **Gemeinsamer Schlüssel für `backtrace` und `diagnose`:** Heute stehen
  beide nur in `[output.console]`/`[output.file]`, wirken aber auf beide
  Ausgaben gemeinsam (`diagnose` an, sobald eine Ausgabe es einschaltet;
  `backtrace` an, solange nicht alle es abschalten), weil die
  Rückverfolgung im meldenden Prozess einmal zu Text wird. Ein Schlüssel
  auf oberster Ebene der Datei soll das ausdrücken; Anwenderdoku 5.3
  danach anpassen.
- **Markdown-Dateien auf einen Absatz je Zeile umstellen** (globale
  Regel): `implementierungsdoku.md`, `fahrplan.md`, `README.md`.
  `anwenderdoku.md` ist schon so geschrieben. Nicht betroffen ist
  `docs/*.md`: Dort gilt die bei mkdocs übliche Form, fester Umbruch bei
  etwa 80 Zeichen (Entscheidung vom 2026-10-22, nach einer Stichprobe der
  Quelltexte von MkDocs, Material for MkDocs und mkdocstrings).

## Vorgemerkt für ein späteres Release

- **Freigabe für die Startmethode `fork`:** bisher nur mit `spawn`
  geprüft; die Anwenderdoku (2, 4.2, 8) sagt das so und kündigt die
  Freigabe für später an.
- **Kritische Fehler samt Rückverfolgung erfassen** (Kapitel 1.4 der
  Implementierungsdoku). Ursprünglich für `0.1.0.dev2` vor dem ersten
  Release vorgesehen, dann bewusst herausgenommen — Zeitpunkt offen,
  nach `0.1.0` neu einzuplanen. Kapitel 1.4 bleibt als Anforderungsskizze
  stehen, ist aber weiterhin nicht geplant, nur gesammelt. Die
  Anwenderdoku (7.2, 8) nennt bis dahin einen Behelf mit `logger.catch`.

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
- GitHub Pages aktiviert (Settings → Pages → Source: „GitHub Actions") —
  vom Entwickler selbst ausgeführt.
- Tag-Ruleset blockierte zunächst jeden Tag-Push, auch den des Owners
  (Bypass-Liste war leer); Bypass für den Entwickler ergänzt.
- Erster Release-Tag `v0.1.0.dev1` gesetzt und gepusht. `Release`-Workflow
  erfolgreich durchgelaufen; `logdruid` 0.1.0.dev1 ist auf PyPI
  veröffentlicht (über die PyPI-API verifiziert).
- Deutsche Anwenderdoku `anwenderdoku.md` geschrieben, als Anleitung für
  die Rückintegration. Ihre Beispiele sind geprüft: alle TOML-Blöcke ohne
  Warnung, das Beispiel aus 4.6 als Lauf, die Grenzen aus 5.3 und der
  Behelf mit `logger.catch` aus 7.2 an Proben beobachtet.
- Korrekturen: Hinweis auf `--log-file` aus `examples/logdruid.toml`
  entfernt; Implementierungsdoku 2.6 (logdruid liest die Kommandozeile
  nicht) und Tabelle 2.8 (Zusatzfelder überleben die Weitergabe heute
  nicht) berichtigt.
- Englische Nutzerdoku für mkdocs aus `anwenderdoku.md` übertragen,
  aufgeteilt auf Seiten in derselben Reihenfolge (`index.md` mit 1–2,
  `how-it-works.md`, `integration.md`, `configuration.md`,
  `libraries.md`, `exceptions.md`, `limitations.md`, `api.md` aus den
  Docstrings). Geprüft: Build `--strict`, alle Sprunganker, TOML-Beispiele
  ohne Warnung. Ohne Korrekturlesen durch den Entwickler veröffentlicht,
  auf dessen Wunsch; Rückmeldungen kommen aus der Rückintegration.
- `examples/logdruid.toml`: auch die übrigen Hinweise zur Kommandozeile
  und zum Fundort im Kopfkommentar berichtigt.
- README auf Projektbeschreibung und Merkmalstabelle reduziert;
  Installation, Verwendung, Konfiguration und API stehen nur noch auf der
  Website, damit die README nicht von der Doku abweichen kann. Links
  absolut, damit sie auch auf PyPI funktionieren.
- `0.1.0.dev2` veröffentlicht: gleicher Code wie `dev1`, bringt die neue
  README nach PyPI. `pip install logdruid` nimmt die Dev-Version, solange
  es keine stabile gibt (mit `pip download` geprüft).
