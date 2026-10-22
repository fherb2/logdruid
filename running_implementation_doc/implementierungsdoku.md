# 1 Zusammenhänge

logdruid ist eine Einrichtungsschicht um [loguru](https://loguru.readthedocs.io/),
gedacht für Anwendungen (nicht Bibliotheken) mit mehreren Prozessen. Es ersetzt
loguru nicht in dem Sinne, dass es dessen API nachbaut — es nutzt sie unverändert
weiter —, sondern übernimmt alles, was eine solche Anwendung zusätzlich braucht
und loguru allein nicht leistet: eine gemeinsame, nach Zeit geordnete Ausgabe über
mehrere Prozesse hinweg, ohne eine Sperre, die über Prozessgrenzen reicht, und die
Übernahme von Meldungen aus eingebundenen Bibliotheken, die über die
Standardbibliothek `logging` melden.

## 1.1 Ablauf aus Sicht der einbindenden Anwendung

Die Reihenfolge, in der eine Anwendung mit logdruid in Berührung kommt:

1. **Einrichten im `main`-Prozess**, einmal, bevor ein Kindprozess entsteht:
   `logdruid.setup(...)` liest die Konfiguration (1.3) und richtet Konsole
   und/oder Datei ein. Einzelheiten der Ausgabe und der Ordnung nach Zeit in
   3.1.

2. **Je Kindprozess, im `main`-Prozess:** `logdruid.link(name)` liefert einen
   `LogLink`, der dem Kindprozess beim Starten mitgegeben wird. Danach wird im
   `main`-Prozess `link.release()` aufgerufen.

3. **Im Kindprozess, als Erstes:** `logdruid.attach(link)` richtet dort die
   Weiterleitung über die Pipe ein. Was vorher in diesem Prozess gemeldet
   wird, geht noch über die Vorgabe-Ausgabe von loguru.

4. **Melden:** Module der Anwendung melden über `from logdruid import logger`
   — das ist der Logger von loguru selbst, unverändert. Eingebundene
   Bibliotheken melden über ihr eigenes `logging`, ohne von loguru oder
   logdruid zu wissen; logdruid übernimmt ihre Meldungen (1.2).

5. **Abbau, im `main`-Prozess, nachdem die Kindprozesse geendet haben:**
   `logdruid.shutdown()` liest die Pipes zu Ende und schreibt, was noch
   zurückgehalten war.

Einzelheiten der Schnittstelle und der internen Umsetzung in 3.1.

## 1.2 Eine Bibliothek einbinden

Bevor eine Bibliothek eingebunden wird, wird beurteilt, wie sie meldet: welche
Logger sie anlegt, auf welchen Stufen, und welche Meldungsmenge je Durchlauf
entsteht. Das Ergebnis sind Einträge in der Konfigurationsdatei, die ihre
Stufen den im Projekt gültigen Bedeutungen zuordnen (2.5) und, wo nötig,
Schwälle eindämmen. Die Vorgaben dazu stehen in 2.7.

## 1.3 Konfiguration

Alles, was logdruid betrifft, steht in einer eigenen Datei neben der
Anwendungskonfiguration, nicht in ihr (Begründung: 2.6). Ein Beispiel mit
Erläuterungen zu jedem Abschnitt liegt unter `examples/logdruid.toml`.

## 1.4 Neues Feature in der Weiterentwicklung: kritische Fehler und ihre Rückverfolgung zuverlässig erfassen

**Hinweis zum Status dieses Kapitels:** Es sammelt nur Anforderungen und
Rechercheergebnisse aus einer Diskussion in dem Anwenderprojekt, für das
logdruid ursprünglich ausgegründet wurde (dort als `Vorgängermodul`,
Projekt `Anwenderprojekt`, Sitzung). Es ist **kein Plan und keine Vorgabe** — alles
Folgende ist Anlehnung, nicht gesetzter Fakt. Die konkrete Gestalt der
logdruid-API dafür, einschließlich Namen und Umfang, entsteht erst in
einer eigenen Planung, wenn dieses Kapitel umgesetzt wird (vorgesehen
als Fahrplan-Schritt zwischen den heutigen Schritten 2 und 3, Ergebnis
dann Version `dev2`).

### Der Anlass

Im Anwenderprojekt zeigten sich beim Herunterfahren zwei Lücken, die
`Vorgängermodul`/logdruid heute nicht schließt:

1. **Eine unerwartete, nicht abgefangene Ausnahme in einem Kindprozess
   geht am Logging vorbei.** Pythons `multiprocessing` schreibt sie
   selbst, direkt nach `stderr` (`Process <Name>:` plus Rückverfolgung;
   belegt im Quelltext von `multiprocessing/process.py`, `_bootstrap`,
   Python 3.12) — ungeordnet zwischen den übrigen Log-Zeilen, in
   falschem Format, nicht in der Logdatei. Weder `sys.excepthook` noch
   `threading.excepthook` greift für einen solchen Kindprozess; beide
   sind für den Hauptthread bzw. andere Threads im selben Prozess
   gedacht.
2. **Selbst wenn eine kritische Meldung den Weg ins Log findet, stehen
   danach noch die Meldungen des geordneten Herunterfahrens** — die
   Rückverfolgung ist dann nicht mehr die letzte, am leichtesten
   auffindbare Zeile.

### Was zur Bedeutung von `CRITICAL` recherchiert wurde

Festgehalten, weil es die spätere Planung begründen soll, nicht als
bereits getroffene Festlegung für logdruid:

- In Pythons `logging` und in loguru ist `CRITICAL` (50) die höchste
  Stufe: „a serious error, indicating that the program itself may be
  unable to continue running" (Python Logging HOWTO). `ERROR` (40)
  bedeutet dagegen: eine Funktion ist gescheitert, die Arbeit geht
  sonst weiter.
- Sowohl `logging.exception()`/`logger.exception()` als auch loguru
  `logger.catch()` melden als Vorgabe auf `ERROR`, nicht auf
  `CRITICAL` — wer `CRITICAL` für „dieser Prozess gibt auf" reservieren
  will, muss das selbst so festlegen, es ergibt sich nicht von selbst
  aus den Standard-Werkzeugen.
- Andere Systeme zum Vergleich: syslog (RFC 5424) kennt über „Error"
  noch drei weitere Stufen (Critical, Alert, Emergency), Pythons
  `SysLogHandler` bildet `CRITICAL` aber immer nur auf „critical" ab.
  Log4j hat ein eigenes `FATAL` über `ERROR` („should be used
  sparingly"), SLF4J dagegen keines. Go kennt `log.Fatal` nicht als
  Stufe, sondern als Handlung (melden, dann `os.Exit(1)`).
- Drei Arten, wie ein Prozess endet, und was davon heute im Log
  ankommt:
  - **Geordnete Kapitulation** — die Anwendung erkennt selbst, dass es
    nicht weitergeht, meldet und beendet sich mit einem Exit-Code
    ungleich 0 (Vorbild: gunicorn meldet einen nicht startenden Worker
    auf `ERROR` mit eigenem Exit-Code, einen hängenden Worker auf
    `CRITICAL`).
  - **Nicht abgefangene Ausnahme, kein `try`** — je nach Ort ein anderer
    Mechanismus zuständig (Hauptthread: `sys.excepthook`; andere
    Threads: `threading.excepthook`, beide austauschbar und beide als
    Vorgabe auf `stderr`; Kindprozesse von `multiprocessing`: keiner
    von beiden, siehe oben). `SystemExit` bleibt in allen drei Fällen
    still.
  - **Harter Tod** — ein Absturz in nativem Code (`SIGSEGV`, `SIGFPE`,
    `SIGABRT`, `SIGBUS`, `SIGILL`) ließe sich über das Modul
    `faulthandler` noch als Python-Rückverfolgung auffangen, aber nur
    nach `stderr` oder in eine offene Datei, nicht über `logging` (der
    Signalhandler darf nur signalsichere Funktionen nutzen). Bei
    `SIGKILL` oder dem OOM-Killer geht im Prozess selbst gar nichts
    mehr; melden kann das nur ein übergeordneter Prozess (Vorbild:
    gunicorns Hauptprozess meldet „Worker (pid:…) was sent SIGKILL!
    Perhaps out of memory?" auf `ERROR`).
- **Die Idee für einen Abschlussbericht** lehnt sich an Kubernetes an:
  Ein Container kann eine kurze Abschlussnachricht nach
  `/dev/termination-log` schreiben; mit
  `terminationMessagePolicy: FallbackToLogsOnError` nimmt Kubernetes bei
  einem Fehlerende ersatzweise das Ende des eigentlichen Logs als
  Abschlussmeldung. Übertragen auf logdruid: Die `CRITICAL`-Meldungen
  eines Laufs am Ende noch einmal wiederholen, als letzte, am leichtesten
  auffindbare Zeilen.

### Erste, unverbindliche Ansätze aus dem Anwenderprojekt

Diese Ansätze wurden dort für `Vorgängermodul` skizziert, und zwar an
Stellen, die dort projektspezifisch benannt sind (eigene Prozessfunktionen,
Startskript). Für logdruid muss erst entschieden werden, welcher Teil
davon als generische API gehört und welcher Teil Sache der einbindenden
Anwendung bleibt:

- Eine Prozessfunktion eines Kindprozesses ließe sich mit einem
  `logger.catch`-artigen Dekorator auf Stufe `CRITICAL` umschließen: Er
  fängt jede nicht abgefangene Ausnahme, schreibt sie mit
  Rückverfolgung über die Pipe ins Log und beendet den Prozess mit
  Exit-Code 1 — ein `SystemExit` mit einer Zahl bleibt dabei auf
  `stderr` still, Python druckt die Ausnahme dann nicht ein zweites Mal.
  Offen: Bietet logdruid dafür selbst einen Dekorator oder eine
  Hilfsfunktion an (Teil der öffentlichen API), oder bleibt das
  Anwendungscode, der nur `logger` und die vorhandenen Bausteine nutzt?
- Der `main`-Prozess könnte sich jede `CRITICAL`-Meldung jedes Prozesses
  merken, mit Rückverfolgung, und sie bei `shutdown()` am Ende noch
  einmal ausgeben, unter einer Überschrift (im Anwenderprojekt
  angedacht: ein- und ausschaltbar über einen Konfigurationsschalter,
  Vorgabe an). Name des Schalters und Wortlaut der Überschrift waren
  dort selbst noch nicht entschieden.
- Ein Kindprozess, der ohne eigene Meldung endet (`SIGKILL`, Absturz in
  nativem Code), hat keine Rückverfolgung beizutragen; die einbindende
  Anwendung (dort: der main-Prozess) bemerkt das Ende trotzdem und
  könnte es selbst auf `CRITICAL` melden, damit auch das im
  Abschlussbericht erscheint. Ob und wie logdruid dafür eine
  Schnittstelle anbietet, ist offen.
- `faulthandler` für native Abstürze wurde nur als Idee notiert: seine
  Ausgabe kann nicht über `logging`/loguru laufen, allenfalls in eine
  eigene Datei oder nach `stderr`, deren Inhalt eine Anwendung später
  selbst ins Log übernehmen könnte.

### Was zur Version `dev2` gehört

Laut Auftrag: die Umsetzung dessen, was aus diesem Kapitel in der
eigentlichen Planung wird, **und** seine Beschreibung in der
Anwenderdokumentation — wie eine Nutzeranwendung dieses Merkmal
einzubauen hat (vergleichbar mit der Beschreibung von `setup`/`link`/
`attach`/`shutdown` in 1.1).

Quellen der Recherche im Anwenderprojekt, dort abgerufen: Python Logging
HOWTO; CPython-Quelltext `logging/__init__.py`, `logging/handlers.py`,
`multiprocessing/process.py` (3.12); Python-Doku zu `sys`, `threading`,
`faulthandler`; loguru-API; RFC 5424 §6.2.1; Quelltext von gunicorn
(`arbiter.py`) und uvicorn (`config.py`, `logging.py`); Kubernetes-Doku
„Determine the Reason for Pod Failure"; Log4j-Doku zu eigenen Stufen;
SLF4J-FAQ; Go-Doku zu `log`.

# 2 Vorgaben

Dieses Segment enthält die projektweiten, prüfbaren Festlegungen zu logdruid.
Es ist bewusst so geschrieben, dass es ohne weiteren Kontext verständlich
bleibt — logdruid hat keine Abhängigkeit außer loguru und der
Standardbibliothek.

## 2.1 Rolle: eine Einrichtungsschicht um loguru

logdruid baut auf loguru auf und ergänzt, was loguru nicht leistet. Beim
Melden gilt die API von loguru unverändert: logdruid gibt den Logger von
loguru selbst weiter, kein eingewickeltes Objekt und keine Unterklasse. Beim
Einrichten lehnt sich seine eigene API an `logger.configure()` von loguru an.
Was loguru leistet, wird genutzt und nicht nachgebaut; wo logdruid dennoch
selbst baut, nennt die Tabelle in 2.8 den Grund.

Grund: Ein Nachbau müsste jede neue Fassung von loguru nachziehen und gewönne
nichts. Wer loguru kennt, findet sich in logdruid sofort zurecht.

Prüfbar: Code in `src/logdruid/__init__.py`, der ein Merkmal von loguru
nachbildet, ohne dass die Tabelle in 2.8 einen Grund nennt, verletzt die
Vorgabe.

## 2.2 Melden

Module der einbindenden Anwendung melden über `from logdruid import logger`;
das ist der Logger von loguru. Bibliotheken, die die Anwendung einbindet,
melden über `logging` der Standardbibliothek; sie hängen weder an loguru noch
an logdruid, und logdruid übernimmt ihre Meldungen (2.4).

Grund: Ein Ort für den Import in der Anwendung, an dem die Einrichtung hängt.
Bibliotheken richten ihr Logging nicht selbst ein, das ist Sache der
Anwendung (Python Logging HOWTO, „Configuring Logging for a Library").

Prüfbar: Ein `from loguru import logger` in einem Modul der Anwendung
außerhalb von logdruid selbst verletzt die Vorgabe, ebenso ein Import von
loguru oder logdruid in einer Bibliothek, die eingebunden werden soll.

## 2.3 Eine Ausgabe im `main`-Prozess

Konsole und Datei werden nur im `main`-Prozess angelegt. Jeder Kindprozess
schreibt seine Meldungen über eine eigene Pipe zum `main`-Prozess, ohne eine
Sperre, die über Prozessgrenzen reicht. logdruid kapselt beide Seiten: Die
Anwendung holt bei logdruid für jeden Kindprozess einen Anschluss (`link()`)
und gibt ihn dem Prozess mit; der Kindprozess ruft als Erstes `attach()` mit
diesem Anschluss auf und legt selbst keine Ausgabe an. Bis dahin gilt in ihm
die Vorgabe-Ausgabe von loguru.

Den Zeitstempel einer Meldung setzt der meldende Prozess beim Aufruf. Der
`main`-Prozess gibt alle Meldungen, auch seine eigenen, nach Zeitstempel
geordnet aus: Er hält jede eingehende Meldung bis zu einem einstellbaren
Zeitfenster zurück (Vorgabe 100 ms) und reiht früher gestempelte vor später
gestempelte ein. Was erst nach Ablauf des Fensters ankommt, geht sofort
hinaus. Ein Fenster von 0 ms schaltet die Ordnung ab. Beim Abbau gibt der
`main`-Prozess alles aus, was die Kindprozesse bis zu ihrem Ende gemeldet
haben, und danach, was noch zurückgehalten ist.

Grund: In eine Datei schreibt so nur ein Prozess, und kein Prozess wartet auf
die Platte eines anderen; blockieren kann ein Kindprozess nur an seiner
eigenen, vollen Pipe. Eine gemeinsame Warteschlange, wie loguru sie mit
`enqueue=True` anlegt, nimmt beim Schreiben eine Sperre über alle Prozesse;
ein hart beendeter Prozess könnte sie für immer halten und damit jeden
weiteren Aufruf des Loggers in jedem Prozess blockieren. Die Ordnung nach Zeit
hält eine Datei lesbar, in die mehrere Prozesse fein melden; ohne sie hinge
die Reihenfolge davon ab, wann der `main`-Prozess welche Pipe liest.

Prüfbar: Eine Ausgabe, die ein Kindprozess selbst anlegt, verletzt die
Vorgabe, ebenso `enqueue=True` und eine Prozessfunktion, in der vor dem
Anschluss über `attach()` schon anderweitig gemeldet wird.

## 2.4 Übernahme aus `logging`

In jedem Prozess gibt ein Handler an der Wurzel von `logging` jede Meldung an
den Logger weiter: mit dem Namen ihres Loggers als Namen, mit der Stufe nach
der Übersetzung (gleichnamige Stufe von loguru, sonst die Zahl), mit einer
Ausnahme samt Rückverfolgung und mit dem Aufrufer in der Bibliothek, damit
Felder wie `{function}` und `{line}` dorthin zeigen. Die Stufe der Wurzel von
`logging` steht auf der niedrigsten Stufe, die in diesem Prozess durchkommen
kann, damit `logging` darunter keine Meldungen erzeugt.

Grund: Ohne Übernahme gäbe `logging` nur ab `WARNING` aus, auf `stderr` und am
Format der Anwendung vorbei, und die Ausgaben wären weder einer Quelle
zuzuordnen noch zu filtern.

## 2.5 Namen, Prozesse und Stufen

Jede Meldung trägt den Namen ihrer Herkunft — den Namen des Loggers bei
Bibliotheken, den Modulnamen bei eigenem Code der Anwendung — und den Namen
ihres Prozesses; beide stehen voll in der Meldung. Die Prozessnamen vergibt
die einbindende Anwendung beim Aufruf von `link()`.

Innerhalb einer Ebene der Konfiguration (2.6) gilt für eine Meldung: der
längste passende Eintrag für ihren Namen — ein Eintrag gilt für seinen Namen
und alles darunter, `somelib` also auch für `somelib.server` —, sonst der
Eintrag für ihren Prozess, sonst `std_level`. Für einen Logger lässt sich
außerdem eine Übersetzung festlegen: welche seiner Stufen hier auf welche
Stufe abgebildet oder verworfen wird. Mit der eingestellten Stufe verglichen
wird die Stufe nach der Übersetzung.

Empfohlene Bedeutung der Stufen (so in `examples/logdruid.toml` erläutert):
`TRACE` ist dauerhaftes Feindetail des regulären Codes, `DEBUG` ist temporärem
Debug-Code vorbehalten, `INFO` ist der reguläre Betriebsablauf, `SUCCESS`
markiert einen Schritt, der hätte scheitern können und es nicht hat. Was eine
eingebundene Bibliothek auf `DEBUG` meldet, ist in aller Regel kein
Debug-Code in diesem Sinne, sondern dauerhaftes Feindetail; es wird beim
Einbinden zugeordnet, in der Regel auf `TRACE` (2.7).

Grund: So lässt sich jeder Prozess und jeder Teil eines Prozesses einzeln
laut oder leise stellen, und der Rest bleibt ruhig. Die Übersetzung passt
fremde Stufen an die Bedeutung an, die sie in der einbindenden Anwendung
haben sollen.

## 2.6 Konfiguration

Alles, was das Logging betrifft, steht in einer eigenen Datei im Format TOML
(Beispiel mit allen Abschnitten: `examples/logdruid.toml`): die Ausgabeziele
mit Datei, Drehung, Aufbewahrung, Farben und Format (Abschnitt `[output]`),
`std_level`, die Stufen je Prozess (`[processes.<name>]`), die Einträge je
Logger mit Stufe und Übersetzung (`[loggers.<name>]`) und das Zeitfenster der
Ordnung. Das Format einer Zeile ist eine Vorlage in der Schreibweise von
loguru, für Konsole und Datei getrennt einstellbar; ohne Angabe gilt das
Vorgabe-Format von loguru. Die Anzeige der Werte von Variablen bei Ausnahmen
(`diagnose` in loguru) ist als Vorgabe aus und einschaltbar.

Wo die Datei liegt, legt die Anwendung fest und übergibt den Pfad an der API.
Übergibt sie keinen, wird die Datei im Verzeichnis des Einstiegspunkts
erwartet (`sys.modules["__main__"].__file__`), nicht im Arbeitsverzeichnis.
Hat die Anwendung keinen Einstiegspunkt als Datei, etwa bei `python -c`,
gelten nur API und Vorgaben, mit einer Warnung. Kindprozesse suchen nicht
selbst; der `main`-Prozess löst die Konfiguration einmal auf und gibt sie mit
dem Anschluss weiter.

Die Werte kommen aus vier Ebenen, von unten nach oben: Vorgaben von logdruid,
Übergabe an der API, Datei, Kommandozeile. Innerhalb einer Ebene füllt
`std_level` alle Namen und Prozesse, die dort keine eigene Stufe haben. Das
Ergebnis einer höheren Ebene ersetzt das der niedrigeren, je Feld: Eine Stufe
aus der Datei ersetzt die Stufen der API, lässt deren Übersetzungen aber
stehen. logdruid liest die Kommandozeile nicht selbst: Die Anwendung wertet
ihre Argumente aus und übergibt die Werte an `setup()` als `cli_level`, das
als `std_level` der obersten Ebene alle Stufen ersetzt, und als
`cli_log_file`, den Pfad der Datei-Ausgabe, der nur wirkt, wenn diese
eingeschaltet ist.

Fehler in der Konfiguration — eine unbekannte Stufe, ein unbekannter
Schlüssel, eine fehlende Datei — erzeugen eine Warnung, keinen Abbruch; an
loguru gehen nur gültige Werte. Ist kein Ausgabeziel eingeschaltet, warnt
logdruid und gibt auf der Konsole aus.

Wird eine Anwendung über einen Einstiegspunkt eines Pakets gestartet
(`[project.scripts]`), ist `__main__` vermutlich das dafür erzeugte
Startskript im `bin`-Ordner der Umgebung (Kenntnisstand, nicht geprüft). Dort
liegt keine eigene Konfigurationsdatei; solche Anwendungen übergeben den Pfad
an der API.

Grund: Die Einstellungen des Loggings sind Wissen der Implementierung über
die eingebundenen Bibliotheken und über die Lautstärke der eigenen Teile; sie
gehören an einen Ort, der mit dem Modul mitwandert, nicht in die
Konfiguration der Anwendung. Fehler im Logging sollen die Anwendung nicht
anhalten.

Prüfbar: Eine Einstellung des Loggings in der Konfigurationsdatei der
Anwendung statt in der von logdruid verletzt die Vorgabe, ebenso ein Abbruch
wegen eines Fehlers in Letzterer.

## 2.7 Einbinden einer Bibliothek

Vor dem Einbau wird beurteilt, wie eine Bibliothek meldet: aus ihrer
Dokumentation und, wenn sie aus Python-Quelltext besteht, aus diesem — welche
Logger sie anlegt, auf welchen Stufen sie meldet und welche Meldungen je
Durchlauf, je Anfrage oder je Ereignis entstehen. Ergebnis sind Einträge in
der Konfigurationsdatei, die ihre Stufen den im Projekt gültigen Bedeutungen
zuordnen (2.5), wo sie nicht schon passen. Zum Abschluss des Einbaus zeigt ein
Lauf auf `TRACE`, ob die Menge der Meldungen je Stufe zur gewählten Bedeutung
passt; wenn nicht, wird die Zuordnung im Einzelfall geändert.

Grund: Eine Bibliothek kennt die Bedeutung der Stufen der einbindenden
Anwendung nicht. Ohne Beurteilung entstehen Schwälle, etwa eine Zeile je
Anfrage auf `INFO`.

Prüfbar: Ein Logger einer eingebundenen Bibliothek, der im Lauf auf `TRACE`
einen unverhältnismäßigen Schwall erzeugt, verletzt die Vorgabe.

## 2.8 Was loguru mitbringt und was logdruid hinzufügt

Stand 2026-10-21, geprüft gegen loguru 0.7.3: an der Dokumentation von loguru
und, wo die Dokumentation nicht reichte, an dessen Quelltext (Dateien in
Klammern). Die Spalte `logdruid` gibt den Stand nach den Vorgaben oben wieder,
nicht unbedingt den heutigen Code. „x" heißt vorhanden, „–" nicht vorhanden;
in der Spalte `logdruid` heißt „–", dass logdruid das Merkmal von loguru nutzt
oder gar nicht braucht. Ein „x" in beiden Spalten heißt: logdruid baut etwas
selbst, was loguru schon leistet, auch wenn loguru es anders umsetzt; die
Anmerkung nennt dann den Grund. Setzt logdruid dasselbe Ziel auf einem
anderen Weg um, stehen beide Wege in getrennten Zeilen.

| Merkmal | loguru | logdruid | Anmerkung |
| --- | --- | --- | --- |
| **Ausgabe und Format** | | | |
| Ausgabe auf die Konsole (`stderr`) | x | – | logdruid richtet sie nur nach der Konfiguration ein. |
| Ausgabe in eine Datei, Drehung nach Größe, Aufbewahrung nach Anzahl | x | – | loguru kann außerdem nach Zeit drehen, komprimieren, die Datei erst bei der ersten Meldung anlegen und sie bei fremder Änderung neu öffnen. |
| Fehlende Verzeichnisse für die Logdatei anlegen | x | – | loguru legt sie selbst an (`_file_sink.py`: `os.makedirs(dirname, exist_ok=True)`); logdruid überlässt es ihm. |
| Format als Vorlage, Farben ein und aus | x | – | logdruid setzt nur Vorlage und Farbschalter. |
| Prozessname und Name der Herkunft in der Meldung | x | – | Felder `{process}` (Kennung und Name, `_logger.py`) und `{name}`. Die Namen der Prozesse vergibt die einbindende Anwendung über `multiprocessing`. |
| Ausgabe als JSON | x | – | `serialize`. |
| Ausnahmen mit erweiterter Rückverfolgung und Werten der Variablen | x | – | `backtrace` und `diagnose`, beide standardmäßig an. Laut loguru ist `diagnose` im Betrieb abzuschalten, weil es Daten preisgeben kann; logdruid schaltet es als Vorgabe aus, in der Konfiguration ist es einschaltbar. |
| **Stufen** | | | |
| Stufen `TRACE` bis `CRITICAL` einschließlich `SUCCESS`; eigene Stufen anlegen | x | – | |
| Mindeststufe je Ausgabeziel | x | – | |
| Stufe je Name, hierarchisch: nächster übergeordneter Eintrag, Vorgabe für alles | x | x | loguru: Filter als Wörterbuch Name → Stufe; gesucht wird vom Namen aufwärts über die Punkte, `""` ist die Vorgabe, `False` schaltet ab (`_filters.py`, `filter_by_level`). logdruid übernimmt diese Bedeutung, baut die Suche aber selbst: Ein Handler filtert für alle Prozesse, und das Wörterbuch von loguru kennt keinen Prozess. Die Filterfunktion von logdruid sucht deshalb erst nach dem Prozess, dann nach dem Namen. |
| Ein- und Ausschalten je Name zur Laufzeit | x | – | `enable`, `disable`, in `configure` als `activation`. |
| Stufe je Prozess | – | x | Schreiben alle Prozesse über eine Ausgabe im `main`-Prozess, hat loguru dafür kein Merkmal; möglich ist es nur über eine eigene Filterfunktion auf dem Feld `process`. logdruid: Tabelle je Prozess in der Konfigurationsdatei, ausgewertet in seiner Filterfunktion. |
| Stufen je Logger übersetzen | – | x | loguru hat dafür kein Merkmal. Möglich wäre es über `patch`, weil die Handler die Stufe erst nach dem Patchen vergleichen (`_handler.py`); anheben lässt sich eine Stufe so aber nur, wenn die ursprüngliche die niedrigste aktive erreicht (`_logger.py`: `level_no < core.min_level`). |
| Unbekannte Stufennamen erkennen | x | x | loguru bricht mit `ValueError: Level '…' does not exist` ab, wenn ein Handler oder ein Filter eine unbekannte Stufe nennt (beobachtet). logdruid prüft vorher und warnt, weil Fehler in der Konfiguration nicht zum Abbruch führen sollen; an loguru gehen nur gültige Werte. |
| **Übernahme aus `logging` der Standardbibliothek** | | | |
| Meldungen aus `logging` an loguru weitergeben | – | x | loguru zeigt dafür nur ein Codebeispiel in seiner Dokumentation („Entirely compatible with standard logging"); im Paket ist es nicht enthalten (Quelltext 0.7.3 durchsucht). logdruid übernimmt das Beispiel. |
| Stufe einer übernommenen Meldung: gleichnamige Stufe von loguru, sonst die Zahl | – | x | Teil desselben Codebeispiels. |
| Loggername als Name einer übernommenen Meldung | – | x | loguru setzt den `__name__` des aufrufenden Moduls ein (`_logger.py`); Bibliotheken mit mehrteiligen Logger-Namen (z. B. `somelib.stream.<name>`) sind damit kein Modulpfad. |
| Stufe der Wurzel von `logging` an die niedrigste aktive Stufe anpassen | – | x | Betrifft `logging`, nicht loguru. |
| Weitergabe von loguru an `logging`, die Gegenrichtung | x | – | Ein `logging.Handler` kann Ausgabeziel sein; hier nicht gebraucht. |
| **Einrichtung und Konfiguration** | | | |
| Nutzbar gleich nach dem Import, vor jeder Einrichtung | x | – | loguru richtet beim Import eine Ausgabe auf `stderr` ab `DEBUG` ein (`__init__.py`, `_defaults.py`); logdruid lässt sie bis zur Einrichtung stehen, eine eigene Übergangsausgabe entfällt. |
| Vorgaben über Umgebungsvariablen ändern | x | – | `LOGURU_LEVEL`, `LOGURU_FORMAT`, `LOGURU_AUTOINIT` und weitere für jeden Parameter von `add` (`_defaults.py`). |
| Gesamte Einrichtung aus einem Wörterbuch, ersetzt alle vorherigen Handler | x | – | loguru: `configure(handlers=…, levels=…, extra=…, patcher=…, activation=…)`; vorhandene Handler werden dabei zuerst entfernt. logdruid richtet über `configure` ein; eigenes Entfernen, Anlegen und die Sperre gegen doppeltes Anlegen entfallen. |
| Konfiguration aus einer Datei lesen | – | x | eigene TOML-Datei (2.6). |
| Rangfolge Vorgabe < API < Datei < Kommandozeile, je Feld | – | x | loguru kennt über seine Vorgaben nur die Umgebungsvariablen. |
| Fundort der Datei neben dem Einstiegspunkt der Anwendung | – | x | |
| Warnung statt Abbruch bei Fehlern in der Konfiguration | – | x | Vergleiche „Unbekannte Stufennamen erkennen". |
| Mindestens ein Ausgabeziel verlangen | – | x | Ohne Handler gibt loguru ohne Hinweis nichts aus. |
| Ein globaler Logger je Prozess, der jeder Einrichtung folgt | x | – | loguru arbeitet mit genau einem globalen `logger`. Ein Prozess, der mit `spawn` entsteht, hat einen eigenen globalen Logger (beobachtet); logdruid richtet ihn im Kindprozess mit dem Anschluss ein und gibt in jedem Prozess den globalen Logger von loguru unverändert als `logger` weiter. |
| Zusatzfelder an Meldungen binden | x | – | `bind`, `contextualize`, `configure(extra=…)`. Nach 2.1 nutzt logdruid das Merkmal von loguru unverändert; der heutige Code erfüllt das nicht: Über die Pipe und auf dem Weg zur Ausgabe gehen nur Zeit, Stufe, Prozess, Name, Modul, Funktion, Zeile und Text mit, sodass `{extra}` in jeder Meldung leer ist, auch im `main`-Prozess, und ein Format mit `{extra[…]}` die Meldung verwirft (beobachtet am 2026-10-22). Dasselbe trifft `{file}`, `{thread}` und `{elapsed}`. Behebung im Fahrplan für das nächste Release vorgemerkt. |
| Mehrere Prozesse schreiben über eine gemeinsame Warteschlange | x | – | `enqueue=True`, bei `spawn` mit `context="spawn"`; die Handler liegen im Elternprozess, der Logger wird an die Kindprozesse übergeben. Die Warteschlange ist eine `multiprocessing.SimpleQueue` (`_handler.py`), deren `put` unter Linux eine Sperre über alle Prozesse nimmt (Python 3.12, `multiprocessing/queues.py`). logdruid nutzt sie deshalb nicht (2.3). |
| Mehrere Prozesse schreiben über je eine eigene Pipe ohne gemeinsame Sperre | – | x | Je Kindprozess eine Pipe zum `main`-Prozess, beide Seiten in logdruid gekapselt; die einbindende Anwendung reicht nur den Anschluss durch. Ein hart beendeter Kindprozess betrifft nur seine eigene Pipe. |
| Meldungen mehrerer Prozesse zeitlich ordnen, mit einstellbarem Fenster | – | x | Ordnung nach dem Zeitstempel, den loguru beim Aufruf im meldenden Prozess setzt (`_logger.py`: `aware_now()`); Vorgabe 100 ms, 0 ms schaltet ab. Ohne Ordnung gilt die Reihenfolge des Eintreffens. |
| Fehler in einem Ausgabeziel abfangen, statt die Anwendung abzubrechen | x | – | `catch=True`, Vorgabe. |
| Ausnahmen in einer Funktion automatisch melden | x | – | `logger.catch` als Dekorator. |
| Teure Argumente erst bei Bedarf auswerten | x | – | `opt(lazy=True)`. |
| Meldung vor der Ausgabe verändern | x | – | `patch`; logdruid nutzt es für den Loggernamen bei übernommenen Meldungen. |
| Logdateien wieder einlesen | x | – | `parse`. |
| Unabhängige Logger mit eigenen Handlern | x | – | über `copy.deepcopy` des Loggers (siehe 3.1, Eigenheit „deepcopy"). |

Quellen, abgerufen am 2026-10-21: loguru, API `logger`
(https://loguru.readthedocs.io/en/stable/api/logger.html); loguru, „Code
snippets and recipes"
(https://loguru.readthedocs.io/en/stable/resources/recipes.html); loguru,
Überblick, Abschnitt „Entirely compatible with standard logging"
(https://loguru.readthedocs.io/en/stable/overview.html); Quelltext von loguru
0.7.3 (`_logger.py`, `_handler.py`, `_filters.py`, `_file_sink.py`,
`_defaults.py`, `__init__.py`).

# 3 Einheiten

## 3.1 Das Modul `logdruid`

Einziges Modul des Pakets: `src/logdruid/__init__.py`. Es importiert nichts
aus einem anderen eigenen Modul und hat außer loguru und der
Standardbibliothek keine Abhängigkeit.

### 3.1.1 Eigenheiten von loguru 0.7.3 und Python 3.12, die die Umsetzung bestimmt haben

Vier Eigenheiten haben die Umsetzung bestimmt. Sie stehen hier, weil die
Docstrings im Code sagen, was er tut, aber nicht, woran er sich stößt.

**Die Warteschlange von loguru nimmt eine Sperre über alle Prozesse.** Belegt
im Quelltext: loguru legt mit `enqueue=True` eine `multiprocessing.SimpleQueue`
an (`_handler.py`), und deren `put` hält unter Linux für die Dauer des
Schreibens eine Sperre über alle Prozesse (`multiprocessing/queues.py`). Ein
hart beendeter Prozess, der sie gerade hält, blockierte jeden weiteren Aufruf
des Loggers in jedem Prozess. Deshalb schreibt jeder Kindprozess über eine
eigene Pipe (2.3). Beobachtet in `tests/test_logging.py`: Ein Kindprozess, der
in schneller Folge meldet und dabei mit `SIGKILL` beendet wird, hält niemanden
auf.

**loguru hängt an jedes Textformat selbst die Ausnahme an.** An ein Format,
das als Text angegeben ist, fügt loguru einen Zeilenumbruch und `{exception}`
an (`_logger.py`, `add`). Ein Format, das `{exception}` selbst enthält, gibt
die Rückverfolgung deshalb doppelt aus. Das Format, mit dem eine Meldung in
die Pipe geht, ist darum nur `{message}`; die Rückverfolgung kommt als Text
mit, weil sich ihr Objekt nicht übertragen lässt.

**`poll()` meldet auch das Dateiende als lesbar.** Eine Pipe, deren Gegenende
geschlossen ist, gilt für `poll()` als lesbar; das folgende `recv()` wirft
`EOFError`. Wer eine Pipe ausliest, muss das Dateiende deshalb beim Lesen
abfangen, nicht beim Abfragen.

**Ein mit `copy.deepcopy` erzeugter Logger ist unabhängig.** Nach dem Rezept
„Creating independent loggers" von loguru hat eine tiefe Kopie des Loggers
eigene Handler. logdruid nutzt das für die Ausgabe im `main`-Prozess, damit
die Sammelstelle nicht über den globalen Logger schreibt, in den sie selbst
einreiht. Beobachtet in der Probe zum Aufbau: Eine solche Kopie führt eine
eigene Datei mit Drehung.

### 3.1.2 Herkunft

Übernommen aus dem Projekt `Anwenderprojekt`, Commit
`f69672f9c6c39cd2291424dc2b11ab8bcd6685ce`, aus `dortiges Logging-Modul` und
`dortige Logging-Konfiguration`. Die Historie wurde nicht mitgenommen; der erste
Commit dieses Repositories nennt Herkunft und Commit-Hash.
