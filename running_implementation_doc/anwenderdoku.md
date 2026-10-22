# logdruid – Anwenderdokumentation

Stand: Version 0.1.1

## 1 Wozu logdruid da ist

[loguru](https://loguru.readthedocs.io/) ist eine Logging-Bibliothek für Python mit genau einem globalen Logger. Gemeldet wird über `logger.info(...)`, `logger.warning(...)` usw.; Ausgaben – Konsole, Datei oder eine eigene Funktion – werden mit `logger.add(...)` angehängt. Jede Ausgabe hat eine Mindeststufe, ein Format als Vorlage mit Feldern wie `{time}`, `{level}`, `{name}` und `{message}` und wahlweise einen Filter.

In einer Anwendung mit mehreren Prozessen stößt loguru allein an Grenzen. Ein Prozess, der mit der Startmethode `spawn` entsteht, hat seinen eigenen globalen Logger mit eigenen Ausgaben. Sollen alle Prozesse in eine gemeinsame Datei schreiben, bietet loguru eine gemeinsame Warteschlange an (`enqueue=True`); deren Schreiben nimmt unter Linux eine Sperre, die über alle Prozesse reicht. Wird ein Prozess hart beendet, während er diese Sperre hält, hängt danach jeder Aufruf des Loggers in jedem Prozess. Außerdem erscheinen Meldungen von Bibliotheken, die über das Modul `logging` der Standardbibliothek melden, nicht in den Ausgaben von loguru.

logdruid ist eine Einrichtungsschicht um loguru für genau diesen Fall: Anwendungen – nicht Bibliotheken – mit mehreren Prozessen. Es baut keine eigene Logging-API: Gemeldet wird weiter mit dem Logger von loguru, unverändert. logdruid richtet ihn nur ein und ergänzt, was loguru nicht leistet: eine gemeinsame, nach Zeit geordnete Ausgabe über alle Prozesse ohne Sperre über Prozessgrenzen, die Übernahme der Meldungen aus `logging` und eine Konfiguration in einer eigenen Datei.

Für eine Anwendung mit nur einem Prozess reicht loguru allein; auch mehrere Threads in einem Prozess sind für loguru kein Problem. Ebenso reicht loguru, wenn jeder Prozess in seine eigene Datei schreiben darf und die Reihenfolge über die Prozesse hinweg keine Rolle spielt. Bibliotheken sollten weder loguru noch logdruid benutzen, sondern über `logging` melden; die einbindende Anwendung übernimmt ihre Meldungen (Kapitel 6).

| Merkmal | loguru allein | mit logdruid |
| --- | --- | --- |
| Melden mit `logger.info(...)` usw., Stufen `TRACE` bis `CRITICAL` einschließlich `SUCCESS` | ja | ja, derselbe Logger und dieselbe API |
| Konsole und Datei, Drehung und Aufbewahrung der Datei, Format, Farben | ja | ja, eingestellt über die Konfigurationsdatei |
| Ausnahmen mit erweiterter Rückverfolgung, wahlweise mit Werten der Variablen | ja | ja; die Werte der Variablen sind als Vorgabe aus |
| Alle Prozesse schreiben in eine gemeinsame Ausgabe | ja, über eine gemeinsame Warteschlange mit Sperre über alle Prozesse | ja, über eine eigene Pipe je Kindprozess, ohne gemeinsame Sperre |
| Ein hart beendeter Prozess hält die anderen nicht auf | nicht sicher, siehe oben | ja |
| Meldungen aller Prozesse nach Zeit geordnet | nein, Reihenfolge des Eintreffens | ja, mit einstellbarem Zeitfenster |
| Mindeststufe je Name einer Meldung (Modul, Logger) | ja, über einen Filter | ja |
| Mindeststufe je Prozess | nein | ja |
| Meldungen aus `logging` übernehmen | nur als Codebeispiel in der Doku von loguru | ja, mit dem Namen des Loggers und mit Übersetzung der Stufen je Logger |
| Konfiguration aus einer Datei, Rangfolge Vorgaben < Anwendung < Datei < Kommandozeile | nein, nur Umgebungsvariablen | ja |
| Fehler in der Konfiguration halten die Anwendung nicht an | nein, eine unbekannte Stufe bricht mit `ValueError` ab | ja, sie erzeugen nur eine Warnung |
| Zusatzfelder aus `bind()` und `contextualize()` in der Ausgabe | ja | ja, auch aus Kindprozessen |

## 2 Installation und Voraussetzungen

```bash
pip install logdruid
```

logdruid braucht Python 3.11 oder neuer und bringt loguru ab Version 0.7.3 als Abhängigkeit mit.

Geprüft und freigegeben ist logdruid für Kindprozesse, die mit der Startmethode `spawn` entstehen (`multiprocessing.get_context("spawn")`). Mit `fork` ist es nicht geprüft; eine Freigabe dafür folgt in einer späteren Version. Geprüft ist es unter Linux mit Python 3.11, 3.12 und 3.13.

**Versionen und Stabilität.** Die Versionsnummer folgt Semantic Versioning. Die Fassungen vor `0.1.0` sind Entwicklungsfassungen (`0.1.0.devN`); bis dahin kann sich noch alles ändern, die Schnittstelle wie das Format der Konfigurationsdatei. Ab `0.1.0` kündigt, solange die erste Zahl `0` ist, eine neue zweite Zahl eine Änderung an, die bestehende Anwendungen anpassen müssen; eine neue dritte Zahl bricht nichts. Welche Namen zur Schnittstelle gehören, steht am Anfang von Kapitel 9; jede Änderung daran und am Format der Datei steht im Änderungsprotokoll `CHANGELOG.md` im Repository.

## 3 Wie logdruid arbeitet

Die folgenden Kapitel setzen dieses Bild voraus.

Konsole und Datei gibt es nur im `main`-Prozess, also in dem Prozess, der die Anwendung startet und die übrigen Prozesse erzeugt. Dort läuft ein Thread von logdruid, der alle Meldungen sammelt und schreibt.

Jeder Kindprozess bekommt beim Start eine eigene Pipe zum `main`-Prozess, in eine Richtung: vom Kindprozess zum `main`-Prozess. Nur dieser eine Kindprozess schreibt hinein, deshalb braucht es keine Sperre über Prozessgrenzen. Blockieren kann ein Kindprozess nur an seiner eigenen Pipe, wenn sie voll ist, weil der `main`-Prozess nicht nachkommt. Endet ein Kindprozess, auch hart, endet seine Pipe; was er bis dahin hineingeschrieben hat, kommt an.

Gefiltert wird dort, wo eine Meldung entsteht. Was die eingestellte Mindeststufe nicht erreicht, geht gar nicht erst durch die Pipe.

Durch die Pipe geht je Meldung alles, was loguru zu ihr festhält: der Zeitstempel, den der meldende Prozess beim Aufruf setzt, und die Zeit seit dessen Start, die Stufe, Name und Kennung von Prozess und Thread, der Name der Meldung, Modul, Funktion, Datei und Zeile des Aufrufs, die mit `bind()` und `contextualize()` angehängten Werte und der fertige Text der Meldung, eine Rückverfolgung als Text eingeschlossen. Der `main`-Prozess setzt diese Angaben beim Schreiben wieder ein, sodass das Format der Ausgabe sie so zeigt, wie der meldende Prozess sie gesetzt hat (Kapitel 5.3).

Der `main`-Prozess reiht seine eigenen Meldungen in dieselbe Ordnung ein. Er hält jede Meldung ein kurzes Zeitfenster lang zurück, als Vorgabe 100 ms, und schreibt die Meldungen dann nach ihrem Zeitstempel geordnet. Eine Meldung, die erst nach Ablauf dieses Fensters ankommt, wird sofort geschrieben, gegebenenfalls also außer der Reihe.

In jedem Prozess übernimmt logdruid außerdem die Meldungen, die über `logging` entstehen, und gibt sie an den Logger von loguru weiter (Kapitel 6).

## 4 Einbau in die Anwendung

Der Einbau hat fünf Stellen:

1. Im `main`-Prozess, einmal, bevor ein Kindprozess entsteht: `logdruid.setup(...)`.
2. Im `main`-Prozess, je Kindprozess: `logdruid.link(...)` vor dem Start, `release()` danach.
3. Im Kindprozess, als Erstes, was mit dem Logging zu tun hat: `logdruid.attach(...)`.
4. Überall: Melden mit `from logdruid import logger`.
5. Im `main`-Prozess am Ende, nachdem alle Kindprozesse geendet haben: `logdruid.shutdown()`.

### 4.1 Einrichten im `main`-Prozess: `setup()`

```python
import logdruid
from logdruid import logger

logdruid.setup()                      # oder logdruid.setup(pfad_zur_datei)
logger.success("Logging aktiv")
```

`setup()` wird einmal aufgerufen, im `main`-Prozess, möglichst früh und bevor der erste Kindprozess entsteht. Der erste Parameter ist der Pfad der Konfigurationsdatei; ohne ihn sucht logdruid die Datei selbst (Kapitel 5.1). Weitere, wahlweise Parameter beschreibt Kapitel 5.5; mit `process_name` lässt sich der Name des `main`-Prozesses in den Meldungen ändern, Vorgabe ist `main`.

`setup()` tut der Reihe nach Folgendes:

- Es setzt den Namen des laufenden Prozesses auf `process_name`.
- Es liest die Konfiguration.
- Es entfernt **alle** bisherigen Ausgaben des globalen Loggers von loguru, auch die Vorgabe-Ausgabe von loguru und jede, die die Anwendung vorher selbst angelegt hat.
- Es legt Konsole und Datei nach der Konfiguration an und startet den sammelnden Thread.
- Es übernimmt `logging` und ersetzt dabei alle Handler an der Wurzel von `logging` (Kapitel 6).
- Es meldet `shutdown()` bei `atexit` an (Kapitel 4.5).
- Zuletzt meldet es Probleme der Konfiguration als Warnungen, sobald es eine Ausgabe gibt (Kapitel 5.7).

Was vor `setup()` gemeldet wird, geht noch über die Vorgabe-Ausgabe von loguru auf `stderr`.

### 4.2 Einen Kindprozess vorbereiten: `link()` und `release()`

```python
import multiprocessing as mp

ctx = mp.get_context("spawn")
link = logdruid.link("worker")
process = ctx.Process(target=worker, args=(link, ...), name="worker")
process.start()
link.release()
```

`logdruid.link(name)` legt die Pipe für einen Kindprozess an und liefert ein `LogLink`-Objekt. Es wird im `main`-Prozess nach `setup()` aufgerufen, einmal je Kindprozess, vor dessen Start; ohne vorheriges `setup()` im selben Prozess wirft es `RuntimeError`. Das `LogLink` wird dem Kindprozess als Argument mitgegeben; es enthält auch die Konfiguration, die der `main`-Prozess aufgelöst hat, sodass der Kindprozess selbst nichts sucht oder liest.

Der Name, der an `link()` geht, ist der Name, den der Kindprozess in jeder seiner Meldungen trägt, sobald er sich angeschlossen hat (Kapitel 4.3), und nach dem sich seine Mindeststufe richten kann (Kapitel 5.4). Der Name, den `multiprocessing` über `name=` vergibt, gilt nur bis dahin. Es empfiehlt sich, beide gleich zu wählen.

`link.release()` gehört direkt hinter `process.start()`, nicht davor, denn `start()` braucht das `LogLink` noch, um es an den Kindprozess zu übergeben. `release()` schließt die Kopie des Schreibendes, die der `main`-Prozess noch hält. Ohne diesen Aufruf endet die Pipe nicht, wenn der Kindprozess endet, und `shutdown()` wartet am Ende vergeblich auf sie (Kapitel 4.5).

`link()` geht nur im `main`-Prozess. Ein Kindprozess kann keinen eigenen Anschluss für einen weiteren, von ihm erzeugten Prozess anlegen. Ein `LogLink` gehört genau einem Kindprozess und darf nicht an einen zweiten weitergereicht werden, denn dann schrieben zwei Prozesse ohne Sperre in dieselbe Pipe.

Zur Erinnerung aus Kapitel 2: Geprüft ist das nur mit Kindprozessen, die mit `spawn` entstehen.

### 4.3 Im Kindprozess: `attach()`

```python
import signal

import logdruid
from logdruid import logger


def worker(link, ...):
    signal.signal(signal.SIGINT, signal.SIG_IGN)   # Entscheidung der Anwendung, siehe unten
    logdruid.attach(link)
    logger.info("worker läuft")
    ...
```

`logdruid.attach(link)` schließt den Kindprozess an. Es setzt den Namen des Prozesses auf den Namen aus dem `LogLink`, entfernt die Vorgabe-Ausgabe von loguru in diesem Prozess, legt stattdessen die Weitergabe in die Pipe an und übernimmt `logging` in diesem Prozess. Eine eigene Ausgabe legt der Kindprozess nie an.

`attach()` sollte das Erste sein, was der Kindprozess mit dem Logging tut. Was er vorher meldet, geht über die Vorgabe-Ausgabe von loguru direkt auf `stderr`: ungeordnet, im Format von loguru und nicht in die Datei.

Zum Abweisen von `SIGINT` im Beispiel: logdruid verlangt das nicht und tut es auch nicht selbst; es ist eine Entscheidung der Anwendung, die aber zu logdruid passt. Ein Strg+C im Terminal schickt `SIGINT` an alle Prozesse im Vordergrund, auch an die Kindprozesse. Jeder Kindprozess bekäme dann an beliebiger Stelle ein `KeyboardInterrupt`, möglicherweise auch mitten im Schreiben einer Meldung in seine Pipe. Eine halb geschriebene Meldung lässt den `main`-Prozess diese Pipe aufgeben; er warnt dann, dass spätere Meldungen dieses Prozesses verloren sind (Kapitel 7.4). Viele Anwendungen lassen deshalb die Kindprozesse `SIGINT` gleich als Erstes abweisen und beenden sie geordnet vom `main`-Prozess aus.

### 4.4 Melden

Jedes Modul der Anwendung meldet über

```python
from logdruid import logger
```

Das ist der globale Logger von loguru selbst, kein Nachbau und keine Hülle. Seine gesamte API zum Melden gilt unverändert: `logger.trace()` bis `logger.critical()`, `logger.success()`, `logger.exception()`, `logger.opt(...)` und so weiter. Der Import über logdruid statt über loguru ist dasselbe Objekt; er hält den Bezug zur Einrichtung an einer Stelle.

Was die Anwendung nach `setup()` oder `attach()` nicht tun sollte, ist die Ausgaben des Loggers selbst zu verändern: `logger.add()` legte eine Ausgabe an, die nur die Meldungen des eigenen Prozesses erhält und an der Ordnung nach Zeit vorbeischreibt; `logger.remove()` und `logger.configure()` trennten die Verbindung zu logdruid. Ausgaben gehören in die Konfigurationsdatei (Kapitel 5).

`logger.bind()` und `logger.contextualize()` wirken wie bei loguru: Die angehängten Werte stehen im Format unter `{extra}` bzw. `{extra[schlüssel]}`, für Meldungen jedes Prozesses. Ein Wert aus einem Kindprozess muss dafür durch die Pipe; lässt er sich nicht pickeln, etwa ein Lock oder eine offene Datei, kommt er als Text an (`str(wert)`), und die Meldung geht nicht verloren. Im `main`-Prozess bleibt jeder Wert das ursprüngliche Objekt.

Empfohlene Bedeutung der Stufen – logdruid erzwingt sie nicht, sie hilft aber beim Einstellen und beim Einbinden von Bibliotheken (Kapitel 6):

- `TRACE`: dauerhaftes Feindetail des regulären Codes.
- `DEBUG`: vorübergehendem Debug-Code vorbehalten.
- `INFO`: der reguläre Ablauf.
- `SUCCESS`: ein Schritt, der hätte scheitern können und es nicht ist.
- `WARNING`: etwas Unerwartetes, die Arbeit geht wie vorgesehen weiter.
- `ERROR`: eine Funktion ist gescheitert, die Arbeit geht sonst weiter.
- `CRITICAL`: dieser Prozess kann nicht weiterarbeiten.

### 4.5 Abbau: `shutdown()`

```python
for process in processes:
    process.join()
logdruid.shutdown()
logger.info("Anwendung beendet")
```

`logdruid.shutdown()` wird am Ende im `main`-Prozess aufgerufen, nachdem alle Kindprozesse geendet haben. Es liest jede Pipe bis zu ihrem Ende, schreibt alles, was noch zurückgehalten ist, und beendet den sammelnden Thread. Danach schreibt der `main`-Prozess seine eigenen Meldungen direkt, ohne Zeitfenster und ohne Ordnung.

Auf das Ende der Pipes wartet `shutdown()` höchstens 5 Sekunden. Läuft dann noch ein Kindprozess oder fehlte ein `release()` (Kapitel 4.2), warnt es mit den Namen der betroffenen Prozesse; deren restliche Meldungen gehen verloren.

`shutdown()` darf mehrfach aufgerufen werden. `setup()` hat es bei `atexit` angemeldet, sodass es beim regulären Ende des Interpreters auch dann läuft, wenn die Anwendung es vergisst. Der ausdrückliche Aufruf nach dem Warten auf die Kindprozesse bleibt der vorgesehene Weg: Dann ist sicher, dass alle Pipes zu Ende sind. Wird der `main`-Prozess selbst hart beendet, läuft `atexit` nicht, und was gerade im Zeitfenster zurückgehalten war, geht verloren.

### 4.6 Ein vollständiges Beispiel

```python
import multiprocessing as mp
import signal

import logdruid
from logdruid import logger


def worker(link, count):
    signal.signal(signal.SIGINT, signal.SIG_IGN)
    logdruid.attach(link)
    for step in range(count):
        logger.info(f"Schritt {step}")


def main():
    logdruid.setup()
    ctx = mp.get_context("spawn")
    link = logdruid.link("worker")
    process = ctx.Process(target=worker, args=(link, 3), name="worker")
    process.start()
    link.release()
    logger.info("Kindprozess gestartet")
    process.join()
    logdruid.shutdown()


if __name__ == "__main__":
    main()
```

Liegt neben diesem Skript keine `logdruid.toml`, warnt logdruid einmal, dass die Datei fehlt, und arbeitet mit seinen Vorgaben: Ausgabe auf die Konsole (`stderr`), Mindeststufe `INFO`, Zeitfenster 100 ms und das Vorgabe-Format von loguru. Dieses Format zeigt den Namen des Prozesses nicht; Kapitel 5.3 zeigt eines, das ihn enthält.

## 5 Konfiguration

### 5.1 Wo die Datei liegt

Die Konfiguration steht in einer eigenen Datei im Format TOML, getrennt von der übrigen Konfiguration der Anwendung. Ihren Pfad übergibt die Anwendung als ersten Parameter von `setup()`; ein relativer Pfad gilt relativ zum Arbeitsverzeichnis.

Ohne Pfad sucht logdruid eine Datei namens `logdruid.toml` im Verzeichnis des Einstiegspunkts der Anwendung (`sys.modules["__main__"].__file__`), nicht im Arbeitsverzeichnis. Hat die Anwendung keinen Einstiegspunkt als Datei, etwa bei `python -c`, sucht logdruid nichts und warnt. Wird die Anwendung als Paket installiert und über einen Einstiegspunkt gestartet (`[project.scripts]`), übergibt sie den Pfad ausdrücklich.

Fehlt die Datei oder lässt sie sich nicht lesen, warnt logdruid und arbeitet mit dem, was die Anwendung übergeben hat, und mit seinen Vorgaben weiter. Kindprozesse suchen nie selbst, sie bekommen die aufgelöste Konfiguration mit dem `LogLink`.

### 5.2 Aufbau

Alle Schlüssel sind wahlweise.

| Schlüssel | Bedeutung | Kapitel |
| --- | --- | --- |
| `std_level` | Mindeststufe für alles, was keine eigene hat | 5.4 |
| `sort_window_ms` | Zeitfenster der Ordnung in Millisekunden | 5.6 |
| `[output.console]` | Ausgabe auf die Konsole | 5.3 |
| `[output.file]` | Ausgabe in eine Datei | 5.3 |
| `[processes.<Name>]` | Mindeststufe für einen Prozess | 5.4 |
| `[loggers.<Name>]` | Mindeststufe für einen Namen, dazu eine Übersetzung der Stufen | 5.4, 6 |

Ein unbekannter Schlüssel erzeugt eine Warnung und wird übergangen.

### 5.3 Ausgaben

Es gibt zwei Ausgaben, die Konsole (`stderr`) und eine Datei, jede mit einer eigenen Tabelle:

```toml
[output.console]
enabled = true
colorize = true
format = "<green>{time:YYYY-MM-DD HH:mm:ss.SSS}</green> | <level>{level: <8}</level> | <cyan>{process.name}</cyan> | <cyan>{name}</cyan>: <level>{message}</level>"

[output.file]
enabled = true
path = "app.log"
rotation = "10 MB"
retention = 5
format = "{time:YYYY-MM-DD HH:mm:ss.SSS} | {level: <8} | {process.name} | {name}: {message}"
```

Zwei Schlüssel gehören logdruid selbst: `enabled` schaltet eine Ausgabe ein oder aus, `path` ist der Pfad der Datei und gilt nur für `[output.file]`. Alle übrigen Schlüssel gibt logdruid unverändert an `logger.add()` von loguru weiter und schreibt sie so, wie loguru sie erwartet (siehe die API-Doku von loguru):

- in beiden Tabellen: `format`, `colorize`, `serialize`, `catch`, `backtrace`, `diagnose`;
- nur in `[output.file]` zusätzlich: `rotation`, `retention`, `compression`, `delay`, `watch`, `mode`, `buffering`, `encoding`.

Die Schlüssel `sink`, `level`, `filter`, `enqueue` und `context` setzt logdruid selbst oder lässt sie nicht zu, `enqueue` deshalb, weil es die gemeinsame Sperre zurückbrächte. Ein solcher oder ein unbekannter Schlüssel erzeugt eine Warnung und wird übergangen.

Als Vorgabe ist die Konsole eingeschaltet und die Datei ausgeschaltet. Ohne `format` gilt das Vorgabe-Format von loguru. Ein relativer Pfad der Datei gilt relativ zum Arbeitsverzeichnis beim Start; fehlende Verzeichnisse legt loguru selbst an.

**Welche Felder das Format verwenden kann.** Alle Felder von loguru, mit den Werten, die der meldende Prozess gesetzt hat (Kapitel 3): `{time}`, `{elapsed}`, `{level}`, `{message}`, `{name}`, `{module}`, `{function}`, `{file}`, `{line}`, `{process}`, `{thread}` und `{extra}`. Zwei Besonderheiten:

- `{elapsed}` ist die Zeit seit dem Start des Prozesses, der meldet; ein Kindprozess zählt ab seinem eigenen Start. Das ist dieselbe Bedeutung, die das Feld bei loguru in jedem einzelnen Prozess hat.
- Eine Rückverfolgung steht im Text der Meldung, also in `{message}`; ein ausdrückliches `{exception}` im Format bleibt leer.

Wie bei loguru selbst gilt: Spricht das Format einen Wert mit `{extra[schlüssel]}` an, muss jede Meldung ihn haben; einer Meldung ohne ihn verweigert loguru das Format und schreibt stattdessen „Logging error in Loguru Handler“ auf `stderr`. Mit `serialize = true` enthält das JSON dieselben Felder.

**`backtrace` und `diagnose`** stehen zwar je Ausgabe in deren Tabelle, wirken aber immer auf beide Ausgaben gleich: `diagnose`, die Anzeige der Werte von Variablen in einer Rückverfolgung, ist an, sobald eine eingeschaltete Ausgabe es einschaltet; `backtrace` bleibt an, solange nicht alle eingeschalteten Ausgaben es abschalten. Der Grund liegt in Kapitel 3: Die Rückverfolgung wird in dem Prozess, der meldet, einmal zu Text, für alle Ausgaben. Am klarsten ist es, beide in beiden Tabellen gleich zu setzen. Als Vorgabe ist `diagnose` aus, wie loguru es für den Betrieb rät, weil es Daten preisgeben kann; `backtrace` ist an.

**Wenn eine Ausgabe nicht zustande kommt:** Ist die Datei eingeschaltet, aber ohne `path`, schaltet logdruid sie mit einer Warnung ab. Ist keine Ausgabe eingeschaltet, warnt es und schreibt auf die Konsole. Lässt sich eine Ausgabe nicht anlegen, etwa weil der Pfad nicht beschreibbar ist, warnt es; ist danach gar keine Ausgabe entstanden, schreibt es auf die Konsole.

### 5.4 Mindeststufen je Prozess und je Name

```toml
std_level = "INFO"

[processes.worker]
level = "DEBUG"

[loggers."myapp.camera"]
level = "TRACE"

[loggers.somelib]
level = "WARNING"
```

`std_level` ist die Mindeststufe für alles, was keine eigene hat.

`[processes.<Name>]` setzt die Mindeststufe für einen Prozess. Der Name ist der, den der Prozess in seinen Meldungen trägt: für einen Kindprozess der Name aus `link()` (Kapitel 4.2), für den `main`-Prozess `process_name` aus `setup()`, als Vorgabe `main`.

`[loggers.<Name>]` setzt die Mindeststufe für einen Namen einer Meldung. Bei eigenem Code der Anwendung ist das der Modulname, etwa `myapp.camera`, bei einer Bibliothek der Name ihres Loggers. Ein Eintrag gilt für seinen Namen und alles darunter: `somelib` gilt auch für `somelib.server`. Passen mehrere Einträge, gilt der längste. Ein Name mit Punkt steht in Anführungszeichen, wie `"myapp.camera"` oben; ohne sie läse TOML `[loggers.myapp.camera]` als verschachtelte Tabelle, und logdruid sähe einen Eintrag für `myapp` mit einem unbekannten Schlüssel `camera`.

Innerhalb der Datei gilt für eine Meldung: der passende Eintrag für ihren Namen, sonst der Eintrag für ihren Prozess, sonst `std_level`. Im Beispiel oben erscheinen Meldungen von `somelib` im Prozess `worker` also erst ab `WARNING`, obwohl der Prozess auf `DEBUG` steht.

Die Stufen heißen wie bei loguru: `TRACE`, `DEBUG`, `INFO`, `SUCCESS`, `WARNING`, `ERROR`, `CRITICAL`; Groß- und Kleinschreibung spielt keine Rolle. Ein unbekannter Name erzeugt eine Warnung, der Eintrag wird übergangen.

Ein weiterer Schlüssel in `[loggers.<Name>]`, `translate`, betrifft nur Bibliotheken, die über `logging` melden; Kapitel 6 beschreibt ihn.

### 5.5 Vier Ebenen: Vorgaben, Anwendung, Datei, Kommandozeile

Die Werte kommen aus vier Ebenen, von unten nach oben:

1. die Vorgaben von logdruid (Tabelle am Ende dieses Abschnitts);
2. was die Anwendung als `defaults=` an `setup()` übergibt – ein Wörterbuch mit demselben Aufbau wie die Datei;
3. die Datei;
4. die Werte von der Kommandozeile, die die Anwendung als `cli_level=` und `cli_log_file=` an `setup()` übergibt.

logdruid liest die Kommandozeile nicht selbst. Die Anwendung wertet ihre Argumente selbst aus und reicht die beiden Werte weiter, unter welchem Namen sie sie auf ihrer Kommandozeile auch anbietet:

```python
import argparse

parser = argparse.ArgumentParser()
parser.add_argument("--log-level")
parser.add_argument("--log-file")
args = parser.parse_args()

logdruid.setup(conf_path, defaults={"std_level": "INFO"},
               cli_level=args.log_level, cli_log_file=args.log_file)
```

`cli_level` ist ein Stufenname und ersetzt jede Stufe aller darunterliegenden Ebenen. `cli_log_file` ist der Pfad der Logdatei; er wirkt nur, wenn die Datei in einer der Ebenen eingeschaltet ist, und schaltet sie nicht selbst ein. `None` heißt bei beiden: keine Angabe.

Wie die Ebenen zusammenwirken, hängt von der Art des Werts ab:

- **Mindeststufen:** Für eine Meldung entscheidet die höchste Ebene, die überhaupt etwas über sie sagt – einen passenden Eintrag für ihren Namen, einen Eintrag für ihren Prozess oder `std_level`. Weil `std_level` für alles gilt, verdeckt eine Ebene mit `std_level` alle Stufen der Ebenen darunter. Deshalb ersetzt `cli_level` alles. Und deshalb wirken Stufen, die die Anwendung über `defaults=` übergibt, nicht mehr, sobald die Datei `std_level` setzt; solche Stufen gehören dann in die Datei.
- **Ausgaben:** Die Tabellen `[output.console]` und `[output.file]` werden Schlüssel für Schlüssel zusammengeführt. Setzt die Anwendung in `defaults=` ein `format` und die Datei nur `enabled` und `path`, bleibt das Format der Anwendung erhalten.
- **Übersetzungen** (Kapitel 6): Es gilt die Übersetzung aus der höchsten Ebene, die für den Namen eine hat. Stufen und Übersetzungen werden getrennt gesucht; ein `std_level` in der Datei verdeckt Übersetzungen aus `defaults=` nicht.
- **`sort_window_ms`:** Es gilt der Wert der höchsten Ebene, die ihn setzt.

Die Vorgaben von logdruid:

| Wert | Vorgabe |
| --- | --- |
| `std_level` | `INFO` |
| `sort_window_ms` | `100` |
| `[output.console]` | eingeschaltet, `diagnose = false`, Format von loguru |
| `[output.file]` | ausgeschaltet, `diagnose = false` |
| `backtrace` | an |

### 5.6 Ordnung nach Zeit

`sort_window_ms` ist das Zeitfenster aus Kapitel 3, in Millisekunden. Ein größeres Fenster ordnet auch dann noch richtig, wenn der `main`-Prozess eine Pipe spät liest, schreibt aber jede Meldung entsprechend später. `0` schaltet die Ordnung ab; die Meldungen erscheinen dann in der Reihenfolge, in der sie ankommen. Ein Wert, der keine Zahl ab 0 ist, erzeugt eine Warnung und schaltet die Ordnung ab.

### 5.7 Fehler in der Konfiguration

Ein Fehler in der Konfiguration hält die Anwendung nie an. logdruid übergeht den fehlerhaften Wert, arbeitet mit dem Rest und meldet jeden Fehler als Warnung, sobald es eine Ausgabe gibt. An loguru gehen nur gültige Werte.

Warnungen entstehen für: eine fehlende, unlesbare oder fehlerhafte Datei, einen unbekannten Schlüssel, einen unbekannten Stufennamen, einen unbekannten oder nicht zugelassenen Schlüssel einer Ausgabe, eine Datei-Ausgabe ohne `path`, keine eingeschaltete Ausgabe, eine Ausgabe, die sich nicht anlegen lässt, ein ungültiges `sort_window_ms` und eine ungültige Übersetzung (Kapitel 6).

**Woran man die Warnungen von logdruid erkennt.** Sie stehen auf der Stufe `WARNING` unter dem Namen `logdruid` (im Format das Feld `{name}`) und tragen den Prozessnamen des `main`-Prozesses. Die Mindeststufen aus Kapitel 5.4 und 5.5 wirken auf sie nicht: Auch mit `std_level = "ERROR"`, mit `cli_level` oder mit einem Eintrag `[loggers.logdruid]` erscheinen sie, in jeder eingeschalteten Ausgabe. Sie werden sofort geschrieben, ohne das Zeitfenster aus Kapitel 3. Dasselbe gilt für die Warnungen, die logdruid während des Laufs zur Übertragung ausgibt (Kapitel 4.5 und 7.4).

### 5.8 Eine vollständige Datei

```toml
# Mindeststufe für alles ohne eigene Stufe.
std_level = "INFO"

# Zeitfenster der Ordnung nach Zeit; 0 schaltet die Ordnung ab.
sort_window_ms = 100

[output.console]
enabled = true
# Farben aus, wenn die Ausgabe in eine Datei oder ein anderes Programm geht.
colorize = true
format = "<green>{time:YYYY-MM-DD HH:mm:ss.SSS}</green> | <level>{level: <8}</level> | <cyan>{process.name}</cyan> | <cyan>{name}</cyan>: <level>{message}</level>"
diagnose = false

[output.file]
enabled = true
# Relativ zum Arbeitsverzeichnis beim Start.
path = "app.log"
rotation = "10 MB"
retention = 5
format = "{time:YYYY-MM-DD HH:mm:ss.SSS} | {level: <8} | {process.name} | {name}: {message}"
diagnose = false

# Ein Prozess feiner als der Rest.
[processes.worker]
level = "TRACE"

# Eine Bibliothek, deren DEBUG dauerhaftes Feindetail ist (Kapitel 6).
[loggers.somelib]
translate = { DEBUG = "TRACE" }
```

Eine ausführlich kommentierte Fassung auf Englisch liegt im Repository unter `examples/logdruid.toml`.

### 5.9 Konfiguration prüfen

Ob eine Konfiguration fehlerfrei ist, lässt sich prüfen, ohne etwas einzurichten, etwa in einem Test der Anwendung oder in ihrer CI:

```python
import unittest
from pathlib import Path

import logdruid


class LoggingConfigTest(unittest.TestCase):

    def test_the_shipped_configuration_has_no_mistakes(self):
        path = Path(__file__).parent.parent / "myapp" / "logdruid.toml"
        self.assertEqual(logdruid.check_config(path), [])
```

`logdruid.check_config()` nimmt dieselben Parameter wie `setup()` für die Konfiguration – `config_path`, `defaults`, `cli_level`, `cli_log_file` – und löst dieselben vier Ebenen auf (Kapitel 5.5). Zurück kommt die Liste der Warnungen, die `setup()` dazu ausgeben würde, leer bei einer fehlerfreien Konfiguration. Es legt keine Ausgabe an und ändert nichts am Logger. Deshalb erkennt es nicht, ob sich eine Ausgabe tatsächlich anlegen lässt, etwa ob der Pfad der Logdatei beschreibbar ist; das zeigt erst `setup()`.

## 6 Bibliotheken einbinden, die über `logging` melden

In jedem Prozess – mit `setup()` im `main`-Prozess, mit `attach()` in einem Kindprozess – setzt logdruid einen Handler an die Wurzel von `logging`. Er gibt jede Meldung, die dort ankommt, an den Logger von loguru weiter:

- mit dem Namen ihres Loggers als Name der Meldung, sodass die Einträge `[loggers.<Name>]` aus Kapitel 5.4 für sie gelten;
- mit ihrer Stufe nach der Übersetzung (unten): mit der gleichnamigen Stufe von loguru, für eine eigene Stufe einer Bibliothek ohne gleichnamige Stufe mit deren Zahl;
- mit einer mitgegebenen Ausnahme samt Rückverfolgung;
- mit dem Aufrufer in der Bibliothek, sodass `{module}`, `{function}` und `{line}` in die Bibliothek zeigen.

Dabei gelten die Regeln von `logging` weiter. logdruid **ersetzt alle Handler an der Wurzel** von `logging`; was die Anwendung dort vorher angelegt hat, ist danach weg. Handler an anderen Loggern bleiben bestehen, und deren Meldungen erreichen logdruid zusätzlich, solange der Logger nach oben weiterreicht – eine Bibliothek, die selbst einen Handler anhängt, erscheint dann doppelt. Ein Logger mit `propagate = False` erreicht die Wurzel nicht, und eine Stufe, die eine Bibliothek an ihrem Logger selbst setzt, filtert vorher. Die Stufe der Wurzel setzt logdruid auf die niedrigste Stufe, die im jeweiligen Prozess durchkommen kann, damit `logging` keine Meldungen erzeugt, die ohnehin verworfen würden.

**Übersetzung der Stufen.** Eine Bibliothek kennt die Bedeutung der Stufen in der Anwendung nicht. Was sie auf `DEBUG` meldet, ist in aller Regel kein vorübergehender Debug-Code im Sinne von Kapitel 4.4, sondern dauerhaftes Feindetail, und manche Bibliothek schreibt auf `INFO` eine Zeile je Anfrage. Dafür gibt es in `[loggers.<Name>]` den Schlüssel `translate`:

```toml
[loggers.somelib]
translate = { DEBUG = "TRACE" }

[loggers."somelib.access"]
translate = { INFO = "TRACE" }

[loggers.noisylib]
level = "WARNING"
translate = { INFO = false }
```

Links steht eine Stufe der Bibliothek, rechts die Stufe, die sie in der Anwendung bekommt, oder `false`, dann wird die Meldung verworfen. Eine Übersetzung gilt wie die Stufe für den Namen und alles darunter; ein Name mit Punkt steht auch hier in Anführungszeichen (Kapitel 5.4). Mit der Mindeststufe verglichen wird die Stufe nach der Übersetzung: Eine nach `TRACE` übersetzte `DEBUG`-Meldung erscheint nur, wenn für ihren Namen und Prozess `TRACE` freigegeben ist. Ein unbekannter Stufenname in einer Übersetzung erzeugt eine Warnung, das Paar wird übergangen; ist `translate` keine Tabelle, wird es mit einer Warnung ganz übergangen. Die Übersetzung betrifft nur Meldungen aus `logging`, nicht die eigenen Meldungen der Anwendung über `logger`.

**Vorgehen beim Einbinden.** Bevor eine Bibliothek in Betrieb geht, lohnt es sich zu beurteilen, wie sie meldet: aus ihrer Dokumentation und, wenn sie aus Python-Quelltext besteht, aus diesem – welche Logger sie anlegt, auf welchen Stufen sie meldet und wie viele Meldungen je Durchlauf, je Anfrage oder je Ereignis entstehen. Daraus werden Einträge mit `level` und `translate`, wo ihre Stufen nicht schon zur Bedeutung in der Anwendung passen. Zum Abschluss zeigt ein Lauf mit `std_level = "TRACE"`, ob die Menge der Meldungen je Stufe passt, besonders auf `INFO`; wenn nicht, wird die Zuordnung nachgestellt.

## 7 Ausnahmen und Abstürze

### 7.1 Gemeldete Ausnahmen

Eine Ausnahme, die die Anwendung selbst meldet – mit `logger.exception(...)` oder mit `logger.opt(exception=True).critical(...)` –, wird in dem Prozess, der meldet, samt Rückverfolgung zu Text und geht so durch die Pipe; `backtrace` und `diagnose` (Kapitel 5.3) wirken dort. In der Ausgabe erscheint die Rückverfolgung genau einmal. `logger.exception()` meldet auf `ERROR`; soll eine Meldung heißen, dass der Prozess nicht weiterarbeiten kann, ist `logger.opt(exception=True).critical(...)` der Weg.

### 7.2 Nicht abgefangene Ausnahmen

Eine Ausnahme, die niemand abfängt, erreicht das Logging derzeit nicht – das ist eine Grenze dieser Version, eine kommende Version schließt sie:

- Im Hauptthread schreibt Python sie über `sys.excepthook` auf `stderr`, in anderen Threads über `threading.excepthook`.
- In einem Kindprozess schreibt `multiprocessing` selbst `Process <Name>:` und die Rückverfolgung direkt auf `stderr`: ungeordnet, nicht im Format der Ausgabe und nicht in der Datei.

Für Kindprozesse gibt es mit loguru schon heute einen Behelf: die Prozessfunktion mit `logger.catch` umschließen.

```python
import sys


@logger.catch(level="CRITICAL", onerror=lambda _: sys.exit(1))
def worker(link, ...):
    signal.signal(signal.SIGINT, signal.SIG_IGN)
    logdruid.attach(link)
    ...
```

Geprüft mit `spawn` unter Linux: Die Ausnahme erscheint mit ihrer Rückverfolgung als `CRITICAL`-Meldung des Kindprozesses geordnet in der Ausgabe, der Prozess endet mit Exit-Code 1, und `multiprocessing` schreibt nichts zusätzlich auf `stderr`. Ohne `onerror` wird die Ausnahme ebenso gemeldet, der Prozess endet aber mit Exit-Code 0, und der `main`-Prozess kann den Fehler nicht erkennen. Der Text, den `logger.catch` voranstellt, nennt als Funktion `run` von `multiprocessing`, nicht die Prozessfunktion; mit dem Parameter `message="..."` lässt er sich ersetzen. Eine Ausnahme vor `attach()` geht noch über die Vorgabe-Ausgabe von loguru auf `stderr`.

Im `main`-Prozess fängt die Anwendung eine Ausnahme, die sie nicht fortsetzen lässt, mit `try` und `except` selbst und meldet sie mit `logger.opt(exception=True).critical(...)`.

### 7.3 Harter Tod eines Prozesses

Wird ein Prozess mit `SIGKILL` beendet, vom Speicherwächter des Systems beendet oder stürzt er in nativem Code ab, kann er selbst nichts mehr melden. Was er bis dahin in seine Pipe geschrieben hat, kommt an, und die übrigen Prozesse melden ungestört weiter; geprüft für `SIGKILL`. Dass und wie ein Kindprozess geendet hat, sieht nur der `main`-Prozess, etwa an `process.exitcode` (negativ, wenn ein Signal ihn beendet hat); er meldet das selbst.

### 7.4 Abgebrochene Übertragung

Bricht ein Kindprozess mitten im Schreiben einer Meldung ab, bleibt eine halbe Meldung in der Pipe. Der `main`-Prozess gibt diese Pipe dann auf und warnt unter dem Namen `logdruid` (Kapitel 5.7): `Logging pipe of <Name> broke off (…); later messages of that process are lost`. Die übrigen Pipes sind davon nicht betroffen. Ein möglicher Anlass ist `SIGINT` aus einem Strg+C (Kapitel 4.3).

## 8 Bekannte Grenzen dieser Version

Zusammengefasst, was die Kapitel davor an Ort und Stelle schon nennen:

- Geprüft und freigegeben nur für Kindprozesse mit der Startmethode `spawn`; die Freigabe für `fork` folgt in einer späteren Version (Kapitel 2).
- Geprüft nur unter Linux, mit Python 3.11 bis 3.13 (Kapitel 2).
- Nicht abgefangene Ausnahmen gehen nicht ins Log, sondern direkt auf `stderr`; für Kindprozesse gibt es einen Behelf mit `logger.catch`. Behebung in einer kommenden Version (Kapitel 7.2).
- Nur Kindprozesse des `main`-Prozesses lassen sich anschließen, keine Prozesse, die ein Kindprozess erzeugt; ein `LogLink` gehört genau einem Prozess (Kapitel 4.2).
- `backtrace` und `diagnose` wirken auf beide Ausgaben gemeinsam (Kapitel 5.3).

## 9 API-Referenz

Zur öffentlichen Schnittstelle gehören genau die Namen dieses Kapitels: `logger`, `setup`, `check_config`, `link`, `attach`, `shutdown`, `LogLink` und `CONFIG_FILE_NAME`. Von `LogLink` sind nur der Typ und `release()` öffentlich. Alles andere ist intern und kann sich ohne Ankündigung ändern; was „Ankündigung“ heißt, steht unter „Versionen und Stabilität“ in Kapitel 2. Importiert wird aus dem Paket: `import logdruid` bzw. `from logdruid import logger, LogLink`.

### `logger`

Der globale Logger von loguru (`loguru.logger`), unverändert weitergegeben. Seine API zum Melden beschreibt die Doku von loguru; was nach dem Einrichten nicht mehr verändert werden sollte, steht in Kapitel 4.4.

### `setup(config_path=None, *, defaults=None, cli_level=None, cli_log_file=None, process_name="main")`

Richtet das Logging im `main`-Prozess ein. Einmal aufzurufen, bevor ein Kindprozess entsteht. Gibt `None` zurück. Fehler in der Konfiguration werden als Warnungen gemeldet und halten die Anwendung nie an.

| Parameter | Typ | Bedeutung |
| --- | --- | --- |
| `config_path` | `Path` oder `str`, wahlweise | Pfad der Konfigurationsdatei; ohne ihn `logdruid.toml` neben dem Einstiegspunkt (Kapitel 5.1). |
| `defaults` | `dict`, wahlweise | Ebene der Anwendung, gleicher Aufbau wie die Datei, über den Vorgaben von logdruid und unter der Datei (Kapitel 5.5). |
| `cli_level` | `str`, wahlweise | Stufe von der Kommandozeile; ersetzt jede Stufe aus Datei und Anwendung, Übersetzungen bleiben. |
| `cli_log_file` | `str`, wahlweise | Logdatei von der Kommandozeile; wirkt nur, wenn die Datei-Ausgabe eingeschaltet ist. |
| `process_name` | `str` | Name des `main`-Prozesses in seinen Meldungen, Vorgabe `main`. |

### `check_config(config_path=None, *, defaults=None, cli_level=None, cli_log_file=None)`

Prüft eine Konfiguration, ohne etwas einzurichten (Kapitel 5.9). Die Parameter bedeuten dasselbe wie bei `setup()`. Gibt die Liste der Warnungen zurück, die `setup()` dazu ausgeben würde, als `list` von `str`; leer bei einer fehlerfreien Konfiguration. Ob sich eine Ausgabe tatsächlich anlegen lässt, erkennt erst `setup()`.

### `link(process_name)`

Bereitet das Logging für einen Kindprozess vor; nur im `main`-Prozess, nach `setup()` und vor dem Start des Kindprozesses (Kapitel 4.2).

| Parameter | Typ | Bedeutung |
| --- | --- | --- |
| `process_name` | `str` | Name, den der Kindprozess in seinen Meldungen trägt. |

Gibt ein `LogLink` zurück, das dem Kindprozess als Argument mitgegeben wird. Wirft `RuntimeError`, wenn in diesem Prozess vorher kein `setup()` lief.

### `attach(log_link)`

Richtet das Logging im Kindprozess ein; als Erstes in der Prozessfunktion aufzurufen (Kapitel 4.3). Ersetzt die Vorgabe-Ausgabe von loguru durch die Weitergabe in die Pipe dieses Prozesses und übernimmt `logging`. Gibt `None` zurück.

| Parameter | Typ | Bedeutung |
| --- | --- | --- |
| `log_link` | `LogLink` | vom `main`-Prozess mitgegeben |

### `shutdown()`

Schreibt alles aus und beendet den sammelnden Thread; nur im `main`-Prozess, nachdem die Kindprozesse geendet haben (Kapitel 4.5). Liest jede Pipe bis zu ihrem Ende, höchstens 5 Sekunden lang, schreibt, was noch zurückgehalten ist, und schreibt danach die Meldungen des `main`-Prozesses direkt. Darf mehrfach aufgerufen werden; `setup()` meldet es bei `atexit` an. Gibt `None` zurück.

### `LogLink`

Was ein Kindprozess braucht, um in den `main`-Prozess zu melden. Entsteht durch `link()`; die Anwendung legt es nicht selbst an und reicht es nur an den Kindprozess weiter. Seine Felder sind intern.

**`release()`** schließt die Kopie des Schreibendes, die der `main`-Prozess hält. Direkt nach dem Start des Kindprozesses aufzurufen; ohne diesen Aufruf endet die Pipe nie, und `shutdown()` wartet vergeblich.

### `CONFIG_FILE_NAME`

Der Name der Datei, die `setup()` ohne `config_path` neben dem Einstiegspunkt sucht: `"logdruid.toml"`.
