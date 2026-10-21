# Fahrplan

## Noch offen

1. **`dev`-Abhängigkeiten in Poetry ergänzen**, sobald feststeht, welche
   gebraucht werden (z. B. ein Lint-/Formatierungstool, siehe Chat vom
   2026-10-21 — das ist keine PyPI-Vorgabe, sondern eigene Wahl).

2. **README.md schreiben** — knappe Nutzerdoku, aus Segment 1 der
   Implementierungsdoku abgeleitet (Ablauf `setup`/`link`/`attach`/
   `shutdown`, Konfigurationsbeispiel).

3. **Ersten Commit erstellen**, der Herkunft und Quellstand-Commit-Hash nennt
   (siehe 3.1.2 der Implementierungsdoku).

4. **GitHub-Repo pushen** (`git push -u origin main`), Rulesets für `main`
   und `v*` sind bereits angelegt (siehe Abschnitt „Vorbereitung auf GitHub"
   im alten Chat-Verlauf von `Anwenderprojekt`).

5. **CI aufsetzen:** `.github/workflows/`, mindestens ein Job, der bei jedem
   Push Tests läuft, und ein Job, der bei einem `v*`-Tag das Wheel baut und
   per PyPI Trusted Publishing hochlädt (OIDC, `id-token: write`,
   `pypa/gh-action-pypi-publish`).

6. **PyPI Trusted Publisher registrieren** (`pypi.org/manage/account/publishing/`,
   „pending publisher"), mit dem exakten Workflow-Dateinamen aus Schritt 5 —
   erst möglich, wenn dieser feststeht, und vor dem ersten Release-Tag.

7. **Vor dem Release:** `twine check dist/*` laufen lassen (prüft, ob das
   README als Beschreibung korrekt rendert — PyPI zeigt sonst nur den
   Rohtext); 2FA auf dem PyPI-Konto aktivieren (seit 2024 für jedes Konto
   Pflicht, nicht nur für kritische Projekte).

8. **Dokumentation entscheiden:** mkdocs (mit mkdocstrings) oder Sphinx.
   Offener Punkt dabei: Das mkdocs-Ökosystem ist 2026 im Umbruch (Material
   for MkDocs geht in den Wartungsmodus zugunsten des Nachfolgers
   „Zensical", der noch Alpha ist) — vor einer Festlegung prüfen, ob das
   noch aktuell ist.

9. **Ersten Release-Tag setzen** (`v0.1.0` o. Ä.), sobald CI und Trusted
   Publisher stehen.

10. **Rückintegration in `Anwenderprojekt`:** `dortiges Logging-Modul`
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
- README.md geschrieben (vorgezogen aus Punkt 2, weil `poetry check` sie
  schon für die Validierung von `pyproject.toml` voraussetzt).
- Poetry 2.5.1 installiert (offizielles Installer-Skript, nutzerlokal unter
  `~/.local/share/pypoetry` / `~/.local/bin`, zuvor inspiziert).
- `poetry install` ausgeführt: Dev-venv unter `.venv/` angelegt, `loguru`
  installiert, Paket im Editable-Modus installiert.
- Testlauf verifiziert: alle 26 Tests (`test_logging.py`, `test_config.py`)
  grün im Poetry-venv.
