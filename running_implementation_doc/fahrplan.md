# Fahrplan

## Noch offen

1. **`0.1.1`: Felder bei der Weitergabe nicht verlieren** (Fehler gegen
   Vorgabe 2.1). Über die Pipe gehen je Meldung nur Zeit, Stufe, Prozess,
   Name, Modul, Funktion, Zeile und Text (`_to_item`/`_write` in
   `logdruid.py`). Dadurch fehlt `{extra}` (Werte aus `bind()`/
   `contextualize()`), auch im `main`-Prozess; `{file}`, `{thread}` und
   `{elapsed}` stimmen nicht; ein Format mit `{extra[...]}` lässt
   Meldungen verschwinden (am 2026-10-22 beobachtet). Vor der Umsetzung
   planen, insbesondere wie Werte übertragen werden, die sich nicht
   pickeln lassen. Danach die Grenze aus der Anwenderdoku (1, 4.4, 5.3, 8)
   und den englischen Seiten entfernen.

2. **`0.2.0.dev1` beginnen**, nach `0.1.1`, damit ein Zweig reicht:
   1. Zu Beginn auf einen Absatz je Zeile umstellen (globale Regel):
      `implementierungsdoku.md`, `fahrplan.md` und `README.md`. Ohne
      inhaltliche Wirkung. Nicht betroffen sind
      `anwenderdoku.md` (schon so geschrieben) und `docs/*.md` (bei mkdocs
      übliche Form, fester Umbruch bei etwa 80 Zeichen; Entscheidung vom
      2026-10-22 nach einer Stichprobe von MkDocs, Material for MkDocs und
      mkdocstrings).
   2. **Kritische Fehler samt Rückverfolgung erfassen** nach Kapitel 1.4
      der Implementierungsdoku: dort nur gesammelt, erst planen, dann
      umsetzen und in der Anwenderdoku beschreiben. Bis dahin nennt die
      Anwenderdoku (7.2, 8) einen Behelf mit `logger.catch`.
   3. **Gemeinsamer Schlüssel für `backtrace` und `diagnose`** auf oberster
      Ebene der Datei. Er ersetzt die Angaben je Ausgabe, ist also ein
      Bruch und gehört deshalb in 0.2 (Entscheidung vom 2026-10-22). Heute
      stehen beide nur in `[output.console]`/`[output.file]`, wirken aber
      auf beide Ausgaben gemeinsam, weil die Rückverfolgung im meldenden
      Prozess einmal zu Text wird. Anwenderdoku 5.3 danach anpassen.

3. **Später: Freigabe für die Startmethode `fork`.** Bisher nur mit
   `spawn` geprüft; die Anwenderdoku (2, 4.2, 8) sagt das so und kündigt
   die Freigabe für eine spätere Version an.

## Erledigt

- GitHub-Repo `logdruid` angelegt (public, Rulesets für `main` und `v*`).
- Lokaler Clone unter `~/git/logdruid`.
- Übernahme des Logging-Moduls und seiner Konfigurationsdatei aus dem
  Anwenderprojekt, dazu `test_logging.py`, `logging_scenarios.py` und die
  Klassen `LoggingLayersTest` und `LoggingConfigWarningsTest` aus einer
  weiteren Testdatei; umbenannt auf `logdruid` und von projektinternen
  Verweisen bereinigt.
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
- Erster Commit, gepusht nach `origin/main`.
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
  „kritische Fehler samt Rückverfolgung erfassen", aus einer Sitzung im
  Anwenderprojekt entnommen. Ausdrücklich als Anlehnung markiert, keine
  Vorgabe.
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
- **Persönliche Angaben und Namen des Anwenderprojekts aus der gesamten
  Historie entfernt** (2026-10-22), mit `git-filter-repo` 2.47.0 in zwei
  Durchgängen: in jeder früheren Fassung jeder Datei, in Commit- und
  Tag-Nachrichten und in Autor, Committer und Tagger. Ersetzt: die
  Adresse durch die noreply-Adresse von GitHub, der Name durch `fherb2`
  bzw. `github.com/fherb2` (`pyproject.toml`, `LICENSE`), Namen und Pfade
  des Anwenderprojekts durch neutrale Wörter. Danach `main` und die Tags
  mit Force gepusht (Bypass im Ruleset vorübergehend), die alten
  Workflow-Läufe gelöscht. In `.git/config` stehen jetzt `user.name =
  fherb2` und die noreply-Adresse; diese Datei wird nicht versioniert,
  auf einem anderen Rechner also nach dem Klonen neu setzen. Alte Klone
  der früheren Historie nicht mehr verwenden.
- **`0.1.0.dev3`**: `check_config()`; die eigenen Warnungen heißen
  `logdruid` und unterliegen keiner Mindeststufe; `Settings` nicht mehr
  öffentlich; öffentliche Schnittstelle und Stabilität in 2.9 festgelegt
  und durch `tests/test_api.py` geprüft; Doku-Fehler aus der Rückmeldung
  der Rückintegration behoben (L1–L5); `CHANGELOG.md`; Projekt-Links und
  feste Kategorien in den Metadaten; README ohne Verweis auf die
  internen Arbeitsdokumente.
- `0.1.0.dev1` und `0.1.0.dev2` auf PyPI gelöscht (vom Entwickler, nach
  `dev3`): Ihre Metadaten trugen noch die frühere Autorenangabe samt
  Adresse. Diese beiden Versionsnummern sind damit auf PyPI dauerhaft
  verbraucht.
- Rückintegration in das Anwenderprojekt abgeschlossen, ohne Fehler
  (Rückmeldung des Entwicklers vom 2026-10-22). Die Befunde, die dabei
  nebenbei auffielen (L1–L5), sind mit `0.1.0.dev3` behoben.
- **`0.1.0` veröffentlicht** (2026-10-22), erste stabile Fassung, Code und
  Schnittstelle wie `0.1.0.dev3`, Kategorie „Production/Stable". Vor dem
  Tag liefen `Tests` (3.11–3.13) und `Docs` in der CI grün; lokal fehlte
  auf dem Rechner `xps` ein passendes Poetry (System-Poetry 1.8.2 liest
  die `[project]`-Tabelle nicht). `0.1.0.dev3` bleibt auf PyPI stehen;
  `pip install logdruid` nimmt jetzt `0.1.0`.
- Entwicklungsumgebung im Projekt (2026-10-22): Poetry 2.x in
  `.venv-poetry/`, das Projekt-venv in `.venv/`, beide in `.gitignore`.
  Ist in der Shell ein anderes venv aktiv (`VIRTUAL_ENV`), nimmt Poetry
  dieses statt `.venv/`; vorher `deactivate`.
- **Zweigmodell eingerichtet** (2026-10-22, Skill `git-branch-model`,
  festgelegt in `.claude/git-branch-model.json`): gearbeitet wird auf
  `dev`; `main` ist der Release-Zweig und bekommt nur bei einem Release
  `dev` per Merge, getaggt wird dort. Der Verwaltungszweig
  `repo-management` trägt nur Dateien, die auf jedem Zweig gleich sein
  müssen (`.gitignore`, `poetry.toml`, `LICENSE`, die drei Workflows,
  die Modell-Datei); sie werden nie gemergt, sondern mit
  `git restore --source=repo-management` übernommen und nur dort
  geändert. `pyproject.toml`, `CHANGELOG.md` und `README.md` gehören
  nicht dazu, weil sie sich mit der Entwicklung ändern. `tests.yml`
  läuft nicht auf `repo-management`.
