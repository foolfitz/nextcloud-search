# OCR: Aufrufform, Deckel und die Messungen dahinter

Diese Seite hält fest, was der OCR-Zweig tut, mit welchen Grenzen er es tut und
woher jede dieser Grenzen kommt. Sie ist bewusst vor dem Code entstanden: die
Phasenrecherche führt fünf Annahmen (A1, A2, A3, A5 und Pitfall 10), von denen
jede einzelne, wenn sie falsch ist, erst zwei Ebenen unter dem sichtbaren Fehler
auffällt. Ein Adressraumfehler im Enkelprozess sieht von außen aus wie ein
kaputtes PDF.

Die Zahlen unten sind gemessen, nicht geschätzt. Wo eine Messung eine
Startannahme widerlegt oder bestätigt, steht beides da, mit Datum, damit später
niemand dieselbe Annahme noch einmal trifft.

## Die Aufrufform

```
tesseract - - -l deu+eng+fra --oem 1 --psm 3 -c tessedit_do_invert=0
```

Umgebung: `OMP_THREAD_LIMIT=1`, verpflichtend, siehe Messung 3.

Die Sprachliste ist seit dem 06.09.2026 dreiteilig, siehe den Nachtrag weiter
unten. Jede gemessene Zahl auf dieser Seite stammt aus Läufen mit `-l deu+eng`
vom 01.09.2026, und die Messkommandos stehen deshalb unverändert so da, wie sie
gelaufen sind.

Ein- und Ausgabe laufen über stdin und stdout, deshalb die beiden Striche. Das
spart je Seite eine Datei mit Nutzerinhalt auf der Platte und eine ganze Klasse
von Aufräumfehlern auf dem Fehlerpfad.

Die Seite wird vorher mit pypdfium2 gerastert:
`page.render(scale=dpi/72, grayscale=True, draw_annots=False)`. Graustufen statt
BGRA, weil tesseract intern ohnehin binarisiert und Farbe das Vierfache an
Speicher kostet.

## Nachtrag 06.09.2026: Französisch kommt dazu

Der Standard ist seit dem 06.09.2026 `deu+eng+fra`, nicht mehr `deu+eng`. Das
Image installiert `tesseract-ocr-fra` in derselben gepinnten Version 1:4.1.0-2
wie die beiden anderen Sprachpakete, und `OCR_LANGUAGE_ALLOWLIST` in
`backend/src/findling/config.py` lässt `fra` seither auf die Kommandozeile.
Französisch steht an dritter Stelle, weil die führende Sprache im Ranking von
tesseract am stärksten wiegt und Deutsch die Sprache der Zielgruppe bleibt; eine
Instanz mit überwiegend französischen Scans dreht die Reihenfolge über
`FINDLING_OCR_LANGUAGES`.

Zwei Abgrenzungen, damit diese Seite nicht mehr behauptet, als gemessen wurde:

1. **Alle Kommandozeilen und alle Zahlen auf dieser Seite sind mit `-l deu+eng`
   entstanden**, am 01.09.2026, und bleiben deshalb unverändert stehen. Eine
   dritte Sprache lädt eine weitere `traineddata` und verändert damit sowohl
   die Laufzeit je Seite als auch die Speicherspitze. Wie stark, ist an dieser
   Stelle nicht gemessen, und eine stillschweigende Umdeutung der alten Zahlen
   auf drei Sprachen wäre eine Behauptung ohne Beleg. Die Nachmessung auf der
   Box (Plan 06.1-18) fährt mit `deu+eng+fra`, und erst deren Ergebnis darf
   diese Tabellen ersetzen.
2. **Der Index hat keine dritte Sprache gelernt.** Die Analysekette von Tantivy
   bleibt Deutsch und Englisch, also kein französisches Stemming, keine
   französischen Stoppwörter, keine französische Kompositazerlegung. OCR
   macht aus Pixeln Wörter, die Analysekette macht aus Wörtern einen Index,
   und nur die erste Hälfte ist heute dreisprachig. Ein französisches Dokument
   wird gelesen und über seine Wörter gefunden, nicht über seine Stammformen.

## Nachtrag 21.09.2026: sechs Sprachen kommen dazu, der Standard bleibt bei drei

Das Abbild installiert seit dem 21.09.2026 (Plan 16-10, Backlog-Eintrag BL-F02)
sechs weitere Sprachpakete: `spa`, `ita`, `nld`, `por`, `dan` und `est`, alle
aus derselben Quelle `tesseract-lang` und alle in derselben harten Fassung
`1:4.1.0-2` wie `deu`, `eng` und `fra`. Jede der sechs wird beim Bau mit
`tesseract --list-langs` geprüft, und `OCR_LANGUAGE_ALLOWLIST` in
`backend/src/findling/config.py` hat deshalb neun Einträge statt drei.

Der Standard bleibt `deu+eng+fra`, und das ist der Kern dieses Nachtrags:
verfügbar ist nicht dasselbe wie eingeschaltet. Jede zusätzliche Sprache lädt
eine weitere `traineddata` und macht jede OCR-Seite langsamer und
speicherhungriger, auf jeder bestehenden Installation, ohne dass es jemand
bestellt hätte. Eine Instanz mit spanischen Scans setzt `FINDLING_OCR_LANGUAGES`
und zahlt genau das, was sie nutzt.

Alle Zahlen dieser Seite bleiben unverändert stehen, aus demselben Grund wie im
Nachtrag vom 06.09.2026: sie sind mit `-l deu+eng` entstanden. An den Deckeln,
an der Auflösung und am Zeitlimit je Seite hat dieser Nachtrag nichts geändert,
und der Index hat keine sechs Sprachen gelernt. Die Analysekette von Tantivy
bleibt Deutsch und Englisch.

## Nachtrag 10.10.2026: Tschechisch als zehnte Sprache

Seit Plan 30-02 (Issue #26) installiert das Abbild ein zehntes Sprachpaket:
`ces`, als `tesseract-ocr-ces` aus derselben Quelle `tesseract-lang` und in
derselben harten Fassung `1:4.1.0-2`. Es wird beim Bau mit
`tesseract --list-langs` geprüft wie die anderen, und `OCR_LANGUAGE_ALLOWLIST`
in `backend/src/findling/config.py` hat damit zehn Einträge: `deu`, `eng`,
`fra`, `spa`, `ita`, `nld`, `por`, `dan`, `est` und `ces`. Der Bild-Beweis
läuft in `.github/workflows/docker.yml` im Schritt "Czech OCR in the image
(CZ-01)" auf amd64 und arm64: eine tschechische Zeile wird im gebauten Abbild
über `-l ces` gelesen (`backend/tests/probe_image_ocr_czech.py`).

Der Standard bleibt `deu+eng+fra`, aus demselben Grund wie oben. Anders als
Französisch hat Tschechisch seit 1.5.0 auch eine Analysekette im Index (`cs`,
ohne Stammformreduktion); die Kette ist eine eigene Einstellung
(`FINDLING_LANGUAGES`) und in `docs/language-analyzers.md`, Abschnitt "Czech",
beschrieben. Die Zahlen dieser Seite bleiben unverändert stehen.

## Nachtrag 15.11.2026: Traditionelles Chinesisch als elfte Sprache

Seit Issue #53 installiert das Abbild ein elftes Sprachpaket: `chi_tra`,
Traditionelles Chinesisch, als `tesseract-ocr-chi-tra` aus derselben Quelle
`tesseract-lang` und in derselben harten Fassung `1:4.1.0-2`. Es wird beim Bau
mit `tesseract --list-langs` geprüft wie die anderen, und
`OCR_LANGUAGE_ALLOWLIST` in `backend/src/findling/config.py` hat damit elf
Einträge. Der Standard bleibt `deu+eng+fra`. Das Paket kostet die Schicht des
Abbilds 2.383.872 Byte, fast ganz die `chi_tra.traineddata` mit 2.366.642 Byte.
Der Bild-Beweis läuft in `.github/workflows/docker.yml` im Schritt
"Traditional Chinese OCR in the image (#53)" auf amd64 und arm64: ein
eingecheckter Streifen mit chinesischem Text (`testdata/ocr-zh/probe-zh-tw.png`,
gezeichnet von `scripts/dev/build_zh_ocr_probe.py`) wird im gebauten Abbild über
`-l chi_tra` gelesen (`backend/tests/probe_image_ocr_chinese.py`).

**Die Schreibweise.** Debian schreibt das Paket mit Bindestrich, tesseract und
die Einstellung mit Unterstrich: `FINDLING_OCR_LANGUAGES=chi_tra+eng`. Wer
`chi-tra` einträgt, bekommt die übliche Warnung, und der Eintrag fällt weg wie
jede Sprache, die das Abbild nicht kennt.

**Ohne `chi_tra` ist ein chinesischer Scan für den Index verloren.** Die
Messung vom 15.11.2026 (`docs/measurements/2026-11-zh-ocr`) liest 63
gerenderte A4-Seiten mit 38.844 Han-Zeichen, Gesetzestext und einen
gemischten Brief, in drei Schriften und drei Behandlungen (sauber, simulierter
Scan, Fax), über genau die Aufrufform dieser Seite. Gezählt wird die
Fehlerrate über die Han-Zeichen allein und der Anteil der
Vier-Zeichen-Folgen, die Token für Token als aufeinanderfolgende Token
zurückkommen, also das, was ein vierstelliger Suchbegriff in `body_zh` so
braucht, wie er eingetippt wurde (die Suche nach 臺 und 台 in beiden Formen
ist nicht mitgezählt und kann nur Treffer hinzufügen):

| `FINDLING_OCR_LANGUAGES` | Fehlerrate Han | Vierer-Folgen gefunden | Leerzeichen zwischen Han-Zeichen | s je Seite |
|---|---|---|---|---|
| `deu+eng+fra` (Standard) | 1,000 (kein einziges Han-Zeichen) | 0,0 % | 0 | 3,18 |
| `chi_tra` | 0,034 | 92,7 % | 370 | 1,82 |
| `chi_tra+eng` | 0,040 | 91,9 % | 332 | 2,67 |
| `chi_tra+deu+eng+fra` | 0,044 | 91,5 % | 325 | 4,50 |
| `deu+eng+fra+chi_tra` | 0,045 | 91,4 % | 26.707 | 4,27 |

Die Sekunden stammen aus einem parallelen Lauf und sind nur untereinander
vergleichbar; die seriellen Werte stehen weiter unten.

**Die Reihenfolge entscheidet.** Steht
`chi_tra` hinter den lateinischen Modellen, setzt tesseract zwischen die
meisten Paare von Han-Zeichen ein Leerzeichen: 26.707 Mal auf diesen Seiten,
gegen 370 Mal mit `chi_tra` allein. Die Suche über `body_zh` merkt davon
nichts, weil die Kette aufeinanderfolgenden Han-Zeichen aufeinanderfolgende
Positionen gibt, was auch dazwischen steht. Der gespeicherte Text behält die
Leerzeichen, und mit ihm die Ausschnitte, der Umbau aus `body_de` und die
Einbettungen. Was sie der semantischen Suche antun, ist nicht gemessen; ein
Nachbearbeitungsschritt, der sie entfernt, wäre eine eigene Änderung mit
eigenen Zahlen und ist nicht Teil dieser.

Daraus folgen Einstellungen nach der Sprache, in der die meisten Scans
einer Instanz stehen:

| Bestand | `FINDLING_OCR_LANGUAGES` | Was es kostet |
|---|---|---|
| nur chinesische Scans | `chi_tra` | nichts: die beste und die schnellste Liste für chinesische Seiten |
| chinesisch und englisch | `chi_tra+eng` | etwas Chinesisch (0,040 statt 0,034), dafür lateinische Wörter sicherer (97,2 % statt 95,6 % auf dem gemischten Brief) |
| überwiegend chinesisch, auch deutsch | `chi_tra+deu+eng+fra` | 2 Fehler in 3.148 Zeichen auf den DACH-Seiten, 325 eingefügte Leerzeichen im chinesischen Text |
| überwiegend deutsch, auch chinesisch | `deu+eng+fra+chi_tra` | 0 Fehler auf den DACH-Seiten, 26.707 eingefügte Leerzeichen im chinesischen Text |

`chi_tra+eng` ist für deutsche Scans die falsche Wahl: ohne `deu` gehen die
Umlaute verloren, auf den DACH-Seiten 63 von 3.148 Zeichen (2,0 %), fast so
viel wie mit `eng` allein im Bericht vom 06.09.2026 (64).

**Deutsche Seiten.** Dasselbe Werkzeug wie im DACH-Bericht, über dieselben
sechs Seiten: `deu+eng+fra+chi_tra` liest sie fehlerfrei,
`chi_tra+deu+eng+fra` mit zwei Fehlern in 3.148 Zeichen, beide Male ein `ü`
als `u` (`für`, `Zürich`). Keiner der beiden kostet einen Suchbegriff:
`Zürich` und `Zurich` ergeben in der deutschen wie in der englischen Kette
denselben Term, und `für` ist ein Stoppwort der deutschen Kette, die gelesene
Form `fur` bleibt dort als zusätzlicher Term stehen; geprüft mit den
ausgelieferten Ketten von `findling.index.analyzer`, die Ausgabe steht in
`rohdaten/fehler.txt` der Messung. Hinten angehängt bleiben die deutschen
Seiten fehlerfrei, die Suche über `body_zh` findet fast so viel wie vorn
(91,4 % statt 91,5 % der Vierer-Folgen), und der Preis sind die Leerzeichen im
gespeicherten chinesischen Text; daher die Wahl nach der Mehrheit oben.

**Zeit und Speicher je Seite**, seriell, je dreimal, Seite 1 von
`testdata/corpus/13-ratsvorlage-scan.pdf` (nicht die Seite von Messung 3) und
eine saubere chinesische Seite:

| Seite | `FINDLING_OCR_LANGUAGES` | Median s | Spitze RSS | Adressraum dieser Seite genügt ab |
|---|---|---|---|---|
| deutsch | `deu+eng+fra` | 0,54 | 88 MiB | 128 MB |
| deutsch | `deu+eng+fra+chi_tra` | 0,60 | 136 MiB | 192 MB |
| deutsch | `chi_tra+deu+eng+fra` | 0,67 | 140 MiB | 192 MB |
| chinesisch | `chi_tra` | 1,27 | 108 MiB | 192 MB |
| chinesisch | `chi_tra+eng` | 1,91 | 127 MiB | 192 MB |
| chinesisch | `chi_tra+deu+eng+fra` | 3,12 | 160 MiB | 192 MB |

Zwei Seiten sagen über den Adressraum wenig, deshalb lief dieselbe Leiter
über alle 69 Seiten der Messung (63 chinesische, sechs DACH-Seiten): mit
`chi_tra` allein genügen 128 oder 160 MB, mit `chi_tra+deu+eng+fra`,
`deu+eng+fra+chi_tra` oder `chi_tra+chi_tra_vert` brauchen 8 bis 16 Seiten
256 MB, keine mehr. Mit `chi_tra` in der Liste reichen die 128 MB von
Messung 2 also nicht mehr für jede Seite. `EXTRACT_ADDRESS_SPACE_BYTES` bleibt
bei 512 MB, dem Doppelten des größten gemessenen Bedarfs.

Die Analysekette für chinesischen Text ist eine eigene Einstellung
(`FINDLING_LANGUAGES` mit `zh`) und in `docs/language-analyzers.md`, Abschnitt
"Chinese", beschrieben. Vereinfachtes Chinesisch (`chi_sim`) ist nicht
installiert und nicht gemessen. Die Seiten der Messung sind gerendert und
absichtlich verschlechtert, kein echter Scan; die Zahlen dieser Seite oberhalb
des Nachtrags bleiben unverändert stehen.

### Senkrechter Satz: `chi_tra_vert` dokumentiert, nicht installiert

**`chi_tra` liest senkrecht gesetzten Text nicht.** Eine Seite des
Urheberrechtsgesetzes in Spalten von oben nach unten und von rechts nach links,
gelesen mit dem festen `--psm 3` der Aufrufform: Fehlerrate über die
Han-Zeichen 0,988, keine einzige Vierer-Folge gefunden. Das senkrechte Modell
`chi_tra_vert` liest dieselbe Seite mit 0,049 und findet 80,7 % der
Vierer-Folgen, allein und zusammen mit `chi_tra`. Das ist **eine einzige
Seite**, ein Hinweis und keine Rate.

Das Paket gibt es in trixie: `tesseract-ocr-chi-tra-vert` `1:4.1.0-2`,
`Architecture: all`, Quelle `tesseract-lang`, 1797 kB installiert, Download
1.092.616 Byte. Es ist nicht installiert, weil es nur hilft, wenn ein Admin es
in die Liste aufnimmt, und dann jede waagerechte Seite rund 1,6 Mal so lange
braucht (`chi_tra+chi_tra_vert` gegen `chi_tra`, bei gleicher Erkennung).
Einschalten heißt zwei Dinge in einer Änderung: die apt-Zeile mit ihrer
`--list-langs`-Prüfung in `backend/Dockerfile` und `chi_tra_vert` in der
Positivliste von `backend/src/findling/config.py`. Die Gates in
`backend/tests/test_ocr_languages.py` lesen den dreiteiligen Namen
`chi-tra-vert` bereits und melden, wenn nur eine der beiden Hälften kommt.

## Die Deckel-Kaskade

Vier Zeitdeckel und ein Speicherdeckel greifen ineinander, und die Reihenfolge
ist die eigentliche Aussage.

| Ebene | Wert | Wer erzwingt | Was beim Reißen passiert |
|---|---|---|---|
| Seiten je Dokument | 30 | `ocr.py` | Schleife endet, Verdikt `indexed(truncated)` |
| Zeit je Seite | 30 s | `subprocess.run(timeout=)` | Seite verworfen, Schleife läuft weiter |
| Weiche Gesamtdeadline im Kind | 600 s | `time.monotonic()` in der Seitenschleife | Schleife endet, Verdikt `indexed(truncated)` |
| Harte Deadline des Elternteils | 660 s | `pipe.poll()` plus `killpg` | Verdikt `failed(timeout)`, Kind wird ersetzt |
| Adressraum | 512 MB | Kernel, `RLIMIT_AS`, vom Enkel geerbt | Enkel stirbt, Verdikt `failed(ocr_failed)` |

Die harte Deadline liegt mit 660 s strikt über der weichen mit 600 s, und das
ist keine Kosmetik. Lägen beide gleich, würde der Elternteil das Kind genau in
dem Moment töten, in dem es seinen Teiltext abliefern will, und der ganze Sinn
von D-08 (teilindexieren statt überspringen) wäre dahin: `indexed(truncated)`
käme in der Praxis nie vor. Die 60 s Abstand sind der Puffer, in dem das Kind
den bereits erkannten Text noch durch die Pipe schiebt.

Die oberen drei Ebenen liefern ein teilindexiertes Ergebnis, die unteren beiden
ein Scheitern. Das ist die ganze Logik der Tabelle.

HEIC-Fotos brauchen beim Dekodieren deutlich mehr Adressraum als JPEG gleicher
Größe, weil es für HEIC keinen verkleinernden Draft gibt: mit der einen
malloc-Arena, auf die das Extraktionskind seit Plan 31-07 begrenzt ist, rund
32 MiB fest plus 7 Byte je Pixel, ein 48-MP-Foto ("HEIF Max") also 358 MiB
(gemessen auf amd64 und arm64, `docs/measurements/2026-10-formate-v15/`,
Abschnitte "HEIC-Dekodier-RAM" und "Eine malloc-Arena im Extraktionskind"). Es
passt damit unter den Standard von 512 MiB mit rund 80 MiB Rest; ein HEIC, das
die Schätzung nicht in den verbleibenden Adressraum legt, endet als
`skipped(too_large)` und lässt sich über `FINDLING_EXTRACT_ADDRESS_SPACE_BYTES`
lesbar machen.

## Abweichung von STACK.md

STACK.md nennt unter "Stack Patterns by Variant" einen OCR-Deckel von
"100 Seiten pro Datei". Hier stehen 30, und das ist eine bewusste Abweichung.

Grund ist die Sperrfrist der Queue. `QueueMapper::LOCK_TIMEOUT` steht auf 900 s.
Ein OCR-Job darf nach der Kaskade oben bis zu 600 s laufen. Bei 100 Seiten wäre
die weiche Deadline die einzige wirksame Grenze, und schon zwei solche Dateien
in einem Claim reißen die Sperrfrist: die Zeilen erscheinen wieder als
`scheduled`, `retries` wird hochgezählt und nach `MAX_DELIVERIES` endet eine Datei
als `failed(repeatedly_stuck)`, obwohl gerade völlig in Ordnung an ihr
gearbeitet wird. Mit 30 Seiten bleibt ein Batch verlässlich unter der Sperrfrist.

Wer die 100 zurückhaben will, muss zuerst `LOCK_TIMEOUT` je Job-Art anheben und
die Batchgröße für `ocr` auf 1 bis 2 senken. Beides, nicht eines von beiden.

## Lease-Rechnung ab Phase 26: Zeilen je Slot

Mit mehreren OCR-Slots rechnet der Container die Sperrfrist nicht mehr über die
Batchgröße, sondern über die Zeilen, die ein Slot in einer Lease schafft
(D-26-13).

- **Lease fest:** `LOCK_TIMEOUTS[ocr]` bleibt 1800 s (PHP und
  `OCR_LOCK_TIMEOUT_SECONDS`). Die Claim-Route bekommt keinen Lease-Parameter.
- **Dateideckel:** harte Deadline plus Download-Marge, also Job-Budget
  plus 2 x 60 s. Beim Standard 600 + 120 = 720 s, am Rand des einstellbaren
  Bereichs 780 + 120 = 900 s.
- **2 Zeilen je Slot:** floor(1800 / 900) = 2 und floor(1800 / 720) = 2
  (`OCR_ROWS_PER_SLOT`). Jeder Slot arbeitet seine Zeilen nacheinander ab, und
  alle enden innerhalb einer Lease.
- **Überschuss per unlock:** Der Poller behält je wirksamem Slot 2 OCR-Zeilen
  des Anspruchs und gibt den Rest sofort per `unlock` zurück, bevor ein Kind
  startet. Die Auslieferung wird erstattet: die Zeile verliert weder ein
  `retries` noch wartet sie auf die Sperrfrist.
- **Slots nie mehr als Zeilen (D-26-07):** Liefert ein alter Companion nur zwei
  Zeilen, laufen höchstens zwei Slots.
- **Batchgrößen (D-26-05, D-26-14):** `KIND_BATCH[ocr]` ist 32 nur im Lane
  `index` (Standard und Leistung, 16 Slots x 2 Zeilen). Im Lane `all` (Sparsam
  und Companion 1.3) bleibt es bei 2.
- **Obergrenze des Job-Budgets:** `OCR_JOB_SECONDS_MAX` = 1800 / 2 - 2 x 60
  = 780 s. Die alte Ableitung über die Batchgröße ergäbe bei 32 Zeilen einen
  negativen Wert.

Beispiel Leistung mit 4 wirksamen Slots: der Anspruch liefert bis zu 32
OCR-Zeilen, der Poller behält 8 und gibt 24 sofort zurück.

## Messprotokoll

**Datum:** 2026-09-01
**Womit:** dem gebauten Laufzeitimage dieses Repositories (`docker build -f
backend/Dockerfile backend`), also genau der Software, die ausgeliefert wird.
**Hardware:** x86_64, 13th Gen Intel Core i5-1335U, 12 sichtbare Kerne, Docker
Desktop unter Windows.
**Versionen im Image:** tesseract 5.5.0, leptonica 1.84.1, libwebp 1.5.0,
libtiff 4.7.0, libpng 1.6.48, Pillow 12.3.0.

**Wichtige Einschränkung vorweg:** die Zielhardware des Projekts ist eine 4- bis
8-GB-Box, oft ARM. Die Zeitwerte unten sind deshalb eine untere Schranke, kein
Erwartungswert. Die Adressraumwerte dagegen sind übertragbar, weil sie an der
Pixelzahl der Seite hängen und nicht an der Rechenleistung.

### Die Messvorlage

`testdata/corpus/02-scan-no-text-layer.pdf` ist als Vorlage untauglich: die
Seite misst 300 x 120 Punkt und die Datei ist 814 Byte groß. Das ist ein
Minimalfall für die Textlayer-Erkennung, keine Seite, an der man Speicher misst.
Für die Messung wurde deshalb im Container eine echte A4-Seite erzeugt, mit
reiner Standardbibliothek nach dem Muster von `scripts/dev/build_corpus.py`:
595 x 842 Punkt, 42 Zeilen deutscher Verwaltungsprosa in Helvetica 12 pt,
WinAnsi-kodiert.

```
python prepare.py 300
# pdf_bytes=4203
# raster=2480x3509 mode=L stride=2480
# png_bytes=526661
# webp_bytes=398340
# tif_bytes=8702442
```

2480 x 3509 Pixel in einem Kanal sind 8,7 MB Rohdaten. `stride` ist hier gleich
`width`, aber darauf darf sich der spätere Code nicht verlassen: pypdfium2
polstert Zeilen, und ein Kodierer, der das ignoriert, liefert bei anderer
Seitenbreite Schrägstreifen statt Text.

### Messung 1 (A3): welcher Motor steckt in den Debian-Sprachdaten

```
tesseract --list-langs
# List of available languages in "/usr/share/tesseract-ocr/5/tessdata/" (3):
# deu
# eng
# osd
```

Danach dieselbe Seite viermal, einmal je Motorwahl:

| `--oem` | Bedeutung | Exitcode | Zeichen | stderr |
|---|---|---|---|---|
| 0 | nur Legacy | 1 | 0 | `Tesseract (legacy) engine requested, but components are not present` |
| 1 | nur LSTM | 0 | 2340 | `Estimating resolution as 452` |
| 2 | Legacy plus LSTM | 1 | 0 | `Tesseract (legacy) engine requested, but components are not present` |
| 3 | Vorgabe, was da ist | 0 | 2340 | `Estimating resolution as 452` |

**Ergebnis: A3 bestätigt.** Die Debian-traineddata sind reine LSTM-Daten
(`tessdata_fast`), der Legacy-Motor ist im Image nicht vorhanden. `--oem 1` und
`--oem 3` liefern byteweise denselben Text.

Warum trotzdem `--oem 1` explizit und nicht der Vorgabewert: `--oem 3` heißt
"nimm, was da ist". Solange nur LSTM da ist, ist das dasselbe. Es wird in dem
Moment nicht mehr dasselbe, in dem jemand ein Legacy-Modell nachlegt oder Debian
den Paketinhalt ändert, und dann verschiebt sich still die Erkennungsqualität
jedes gescannten Dokuments. Der explizite Wert macht aus dieser stillen
Verschiebung eine Änderung, die im Diff steht.

### Messung 2 (A1): reichen 512 MB Adressraum

Das Sandbox-Kind setzt `RLIMIT_AS` auf 512 MB, und ein per `subprocess`
gestarteter tesseract erbt dieses Limit. Gemessen wurde über `ulimit -v` in
Kilobyte, weil das genau derselbe Kernelmechanismus ist.

```
bash -c 'ulimit -v 131072; exec tesseract - - -l deu+eng --oem 1 --psm 3 \
    -c tessedit_do_invert=0 < page.png > out.txt'
```

| `ulimit -v` | entspricht | mit `OMP_THREAD_LIMIT=1` | ohne |
|---|---|---|---|
| 131072 | 128 MB | Exitcode 0, 2340 Zeichen | **Exitcode 134**, 0 Zeichen |
| 196608 | 192 MB | Exitcode 0, 2340 Zeichen | Exitcode 0, 2340 Zeichen |
| 262144 | 256 MB | Exitcode 0, 2340 Zeichen | Exitcode 0, 2340 Zeichen |
| 327680 | 320 MB | Exitcode 0, 2340 Zeichen | Exitcode 0, 2340 Zeichen |
| 393216 | 384 MB | Exitcode 0, 2340 Zeichen | Exitcode 0, 2340 Zeichen |
| 458752 | 448 MB | Exitcode 0, 2340 Zeichen | Exitcode 0, 2340 Zeichen |
| 524288 | 512 MB | Exitcode 0, 2340 Zeichen | Exitcode 0, 2340 Zeichen |

**Ergebnis: A1 bestätigt, und mit reichlich Luft.** Eine A4-Seite bei 300 dpi
braucht mit der Pflichtvariablen unter 128 MB Adressraum. Die 512 MB des
Sandbox-Kindes sind also rund das Vierfache des Bedarfs.

**Folge für den Code: der OCR-Zweig bekommt keinen eigenen, höheren
`RLIMIT_AS`.** Die Recherche hatte diesen Ausweg für den Fall vorgesehen, dass
512 MB nicht reichen. Sie reichen. `EXTRACT_ADDRESS_SPACE_BYTES` bleibt
unverändert bei 536870912, und es kommt keine zweite Speicherkonstante dazu, die
gepflegt werden müsste.

Der Rasterschritt selbst wurde unter denselben Grenzen geprüft, weil er im
gleichen Kind läuft:

```
bash -c 'ulimit -v 262144; exec python prepare.py 300'
```

Bei 256 MB, 384 MB, 512 MB und 768 MB jeweils Exitcode 0. Python, pypdfium2 und
Pillow zusammen passen also ebenfalls bequem in das bestehende Limit.

### Messung 3 (A2): Zeit je Seite, und was OMP_THREAD_LIMIT wirklich bringt

Dieselbe Seite, dreimal je Einstellung, Angaben in Millisekunden:

| `OMP_THREAD_LIMIT` | Lauf 1 | Lauf 2 | Lauf 3 | Median |
|---|---|---|---|---|
| 1 | 1984 | 1883 | 2250 | **1984** |
| nicht gesetzt | 2555 | 2424 | 2382 | **2424** |

**Ergebnis: A2 bestätigt, die Variable ist doppelt begründet.** Ein Thread ist
auf dieser Maschine rund 18 Prozent schneller als die Vorgabe, obwohl zwölf
Kerne sichtbar sind. Das deckt sich mit der Tesseract-FAQ, die mehrere Threads
auf kleinen Maschinen ausdrücklich als langsamer beschreibt.

Der zweite Grund steht in der Tabelle von Messung 2 und wiegt schwerer als die
18 Prozent: **ohne die Variable stirbt derselbe Lauf bei 128 MB mit Exitcode
134.** OpenMP reserviert je Thread Stack und Arenen, und `RLIMIT_AS` zählt
virtuellen Adressraum, nicht residenten Speicher. `OMP_THREAD_LIMIT=1` ist damit
keine Feinabstimmung, sondern Teil der Speicherzusage.

Zur Einordnung der 2 Sekunden: der Deckel "Zeit je Seite" steht auf 30 s, also
dem Fünfzehnfachen des hier gemessenen Medians. Das ist Absicht. Die
Zielhardware ist eine ARM-Box mit zwei bis vier langsameren Kernen, und eine
dichte, schlecht gescannte Seite kostet ein Vielfaches einer sauber gerenderten.
Der Deckel soll den Ausreißer abschneiden, nicht den Normalfall.

### Messung 4 (A5): liest leptonica WebP

Jede Datei direkt auf stdin an tesseract, ohne Umweg über Pillow:

| Format | Exitcode | Zeichen | stderr |
|---|---|---|---|
| WebP | 0 | 2340 | `Estimating resolution as 452` |
| TIFF | 0 | 2340 | `Estimating resolution as 452` |
| PNG | 0 | 2340 | `Estimating resolution as 452` |

WebP und PNG liefern byteweise denselben Text.

**Ergebnis: A5 widerlegt in der befürchteten Richtung, und das ist die gute
Nachricht.** Das leptonica 1.84.1 im Image ist gegen libwebp 1.5.0 gebaut und
liest WebP direkt. Der in der Recherche vorgesehene Ausweg, WebP vorher mit
Pillow nach PNG zu wandeln, ist für die reine Lesbarkeit nicht nötig.

Das ändert allerdings nichts daran, dass Plan 03-10 Bilddateien trotzdem durch
Pillow schickt, und der Grund hat mit dem Format nichts zu tun: EXIF-Rotation,
die Bombenprüfung über `Image.MAX_IMAGE_PIXELS`, das Herunterskalieren großer
Handyfotos und die Plausibilitätsprüfung aus D-05 brauchen alle einen Blick in
den Header, bevor tesseract überhaupt startet. Die Messung nimmt dem Umweg nur
die Begründung "sonst geht es gar nicht"; die anderen Begründungen bleiben.

### Messung 5: wie ein Speichertod von außen aussieht

Derselbe Aufruf mit absichtlich zu wenig Adressraum:

```
bash -c 'ulimit -v 65536; exec tesseract - - -l deu+eng --oem 1 --psm 3 \
    -c tessedit_do_invert=0 < page.png'
# rc=134
# terminate called after throwing an instance of 'std::bad_alloc'
```

**Ergebnis: Pitfall 10 bestätigt.** Der Enkel stirbt mit SIGABRT, also Exitcode
134, nach einem C++-`bad_alloc`. Im Sandbox-Kind kommt **kein** `MemoryError`
an, weil nicht das Kind den Speicher angefordert hat. Der OCR-Zweig muss diesen
Fall deshalb selbst erkennen und auf ein eigenes Verdikt abbilden, statt auf die
`MemoryError`-Behandlung der Textextraktion zu hoffen. Ein Exitcode ungleich
null wird zu `failed(ocr_failed)`.

`stderr` wandert dabei nicht in den Log. Tesseract schreibt dort Dateinamen und
inhaltsbezogene Warnungen, und die Regel aus Phase 2 (T-02-107: der Log trägt
Zähler und Reason-Codes, sonst nichts) gilt hier unverändert.

## Die Textlayer-Erkennung

Diese Entscheidung fällt vor jedem OCR-Aufruf und ist die teuerste der ganzen
Kaskade: Sie sagt, ob ein PDF überhaupt in die OCR-Spur geht. Ab dieser Phase
ist der Fehler nicht mehr symmetrisch billig. Ein Text-PDF, das fälschlich
gerastert und durch tesseract geschickt wird, kostet nach der Deckel-Kaskade
oben bis zu 600 Sekunden CPU, für einen Text, der schon dastand.

**Datum:** 2026-09-01
**Womit:** dem Referenzkorpus dieses Repositories im Stand des Messtags,
33 Dateien, davon 19 PDFs, gelesen mit der `pypdfium2` 5.13.0 aus
`backend/uv.lock`. Die Tabelle unten ist die Messung von damals und bleibt
es; der Korpus ist seither gewachsen, und wie groß er heute ist, steht in
`testdata/CORPUS.md` und nirgends sonst.

```
cd backend && uv run python -c "
from pathlib import Path
import pypdfium2
for path in sorted(Path('../testdata/corpus').glob('*.pdf')):
    document = pypdfium2.PdfDocument(str(path))
    counts = []
    for number in range(min(len(document), 30)):
        page = document[number]
        textpage = page.get_textpage()
        counts.append(len(textpage.get_text_bounded().strip()))
        textpage.close()
        page.close()
    document.close()
    print(path.name, counts)
"
```

Zeichen je Seite, nach `strip()`:

| Datei | Seiten | Gemessen | Was die Seite ist |
|---|---|---|---|
| `14-pacht-mit-anhang.pdf` | 5 | 456, 442, 0, 0, 0 | zwei volle A4-Seiten Verwaltungsprosa, dahinter drei gescannte Anlagen |
| `09-bescheid.pdf` | 1 | 123 | drei kurze Zeilen |
| `01-text-layer.pdf` | 1 | 63 | zwei kurze Zeilen |
| `29-doppelt-komprimiert.pdf` | 1 | 29 | eine Zeile, die dünnste echte Textseite des Korpus |
| `31-riesenformat.pdf` | 1 | 12 | nur eine Überschrift, auf 14400 x 14400 Punkt |
| `13`, `15`, `16`, `30` und die Anlagen von `14` | 9 | jeweils 0 | gerenderte Scans |

**Die wichtigste Zahl ist die Null.** Eine gerasterte Seite misst nicht wenig,
sondern exakt nichts: Es gibt kein Textobjekt, über das sich streiten ließe.
Der Korpus allein würde deshalb jede Schwelle zwischen 1 und 12 zulassen, und
genau deshalb ist er nicht der ganze Maßstab.

**Gewählt: `_MIN_CHARS_PER_PAGE = 25`, unverändert, jetzt aber belegt.** Die
Zahl muss die Frage beantworten, die der Korpus nicht stellt: Was trägt eine
Seite, auf der nur ein Stempel steht? Eine gemessene Prosazeile ist 38 Zeichen
breit, ein aufgestempeltes "Seite 3 von 40" sind 14 Zeichen, und die dünnste
echte Textseite der Messung hat 29. Die 25 liegen zwischen diesen beiden
Nachbarn und näher an der echten Seite, weil der Fehler jetzt in Richtung
OCR-Kosten teuer ist. Annahme A2 aus der Phasenrecherche überlebt damit ihre
Messung und hört auf, eine Annahme zu sein.

**Zweite Zahl: `_SCAN_PAGE_SHARE = 2/3`.** Je Seite zu zählen ist nur die halbe
Antwort auf Bug M2 aus dem Phase-2-Audit; die andere Hälfte ist, dass eine
einzelne Seite gar nichts entscheiden darf. Zwei gemessene Fälle klammern den
Wert ein:

| Fall | Anteil Seiten unter der Schwelle | Richtiges Verdikt |
|---|---|---|
| `14-pacht-mit-anhang.pdf`, zwei lesbare Seiten plus drei gescannte Anlagen | 3 von 5, also 0,60 | `indexed` |
| Deckblatt mit Text plus neun Scanseiten | 9 von 10, also 0,90 | `skipped(no_text_layer)` |

Genau zwei Drittel gelten noch als Dokument mit Textlayer: Der Vergleich im Code
ist echt größer, also werden 2 von 3 gescannten Seiten extrahiert und 3 von 4
nicht.

**Der Realfall, den beide Extreme falsch behandeln,** ist die Pachtvereinbarung
mit ihren drei eingescannten Anlagen, und "beide" ist wörtlich gemeint. Der alte
Dokumentdurchschnitt hätte 898 Zeichen gegen 5 mal 25 gerechnet und das Dokument
indexiert, samt drei Anlagen, die danach nie wieder jemand ansieht. Eine Regel
"eine Seite ohne Text heißt Scan" hätte dieselbe Datei komplett durch tesseract
geschickt, für einen Text, der auf den ersten beiden Seiten bereits maschinell
lesbar dastand. Nur die Kombination aus Zählung je Seite und Anteilsregel
behandelt sie richtig.

**Was der gemischte Fall nicht tut:** Die drei Anlagenseiten werden in v1 nicht
zusätzlich OCR-t. Eine Datei hat genau ein Verdikt, und ein zweiter Teil-Job je
Datei wäre eine eigene Mechanik mit eigenem Warteschlangeneintrag, eigenem
Versuchszähler und einer eigenen Art, halb fertig zu sein. Die Anlage einer
Pachtvereinbarung ist diese Mechanik nicht wert; die Entscheidung steht als
Kommentar an derselben Stelle im Code.

**Nebenbefund, der in die Deckel-Kaskade gehört:** `26-riesige-seitenzahl.pdf`
sind 627 Byte, die 100000 Seiten deklarieren, und `len(document)` liefert
tatsächlich 100000. Erst der Seitendeckel macht daraus 30 Leseversuche, von
denen der zweite mit `Failed to load page` endet. Ohne den Deckel wäre die
Schleife hunderttausend Fehlversuche lang. Die Datei liegt genau dafür im
Korpus (Bedrohung T-03-601), und sie ist in unter zehn Millisekunden fertig.

## Die DACH-Abnahme, und warum sie kein Rohtextvergleich ist

Die Abnahme zu D-09 prüft, dass ein Schweizer Dokument mit der Schreibweise ss
und mit dem scharfen s auffindbar ist und ein österreichisches über seine eigene
Wortform. Sie läuft im Integrationslauf als drei Suchen über die gewöhnliche
Suchroute; die Tabelle mit den gemessenen Trefferzahlen und die Begründung je
Zeile stehen in `docs/german-analyzer.md` unter "The DACH cases".

Die Form der Prüfung ist dabei die eigentliche Entscheidung. Naheliegend wäre,
den erkannten Text einer Seite mit einer erwarteten Zeichenfolge zu vergleichen.
Das wäre ein Test gegen die tesseract-Version und nicht gegen dieses Projekt: die
Engine ist an den Digest des Basis-Image gebunden, nicht an eine gepinnte
Version, und schon ein Debian-Punktrelease verschiebt einzelne Zeichen. Die
Messung oben zeigt genau das im Kleinen. Der Lauf im Container liest die fette
Überschrift von `19-uebermittlung.tif` als "Ubermittlungsprotokoll", ohne die
beiden Punkte, während die vier kleingeschriebenen Umlaute der anderen Bilder
unversehrt zurückkommen. Ein Rohtextvergleich wäre daran rot geworden. Die Datei
ist trotzdem über "Übermittlungsprotokoll" auffindbar, weil die deutsche Kette
den Umlautakzent im Stemmer entfernt und beide Schreibweisen auf denselben Term
fallen.

Die Zusage lautet deshalb: der Begriff findet das Dokument. Sie lautet nicht: die
Engine liest die Seite zeichengenau. Das Zweite verspricht dieses Projekt an
keiner Stelle, und der Unterschied ist der Grund, warum die Abnahme über
Suchbegriffe läuft. Was ein Suchbegriff nicht abdeckt, deckt auch niemand sonst
ab: ein Wort, das die Engine gar nicht gelesen hat, fällt durch, und genau das
soll es.

### Nachtrag 06.09.2026: neben dem Gate steht jetzt eine Messung

Der Absatz oben bleibt richtig, jedes Wort davon. Er beantwortet nur eine Frage
nicht, und der Owner hat sie in der Launch-Härtung gestellt: liest die Kette die
Umlaute, die Datums- und die Währungsformate der DACH-Region sauber. Das ist eine
Frage nach der Erkennungsqualität, und ein Suchtreffer kann sie nicht
beantworten. Ein Zeichen, das die Engine falsch liest, ist in einem Wort, das
trotzdem auf denselben Term stemmt, für eine Suche unsichtbar.

Die Trennung, die dieses Projekt an mehreren Stellen schon macht, löst das, ohne
die Begründung oben zu brechen:

- **Das Gate bleibt ein Suchtreffer.** Es ist unverändert, es ist robust gegen
  Engine-Fassungen, und es wird von der Messung weder ersetzt noch verschärft.
- **Die Messung steht daneben.** `findling.extract.ocr_quality` rechnet die
  Zeichenfehlerrate gegen die bekannte Wahrheit. Die Wahrheit ist da, ohne ein
  fremdes Korpus: `scripts/dev/build_corpus.py` rendert die Scans aus eigener
  Prosa und schreibt sie nach `testdata/corpus-truth.json`, byteweise.
- **Die Messung sagt nur Zahlen.** Weder der erkannte noch der erwartete Text
  und kein Pfad verlässt das Werkzeug; die Aufschlüsselung läuft über die
  Sprachvariante `de`, `ch` oder `at`.

Der Aufruf, gegen den Korpus dieses Repositories:

```
python -m findling.extract.ocr_quality \
    --corpus testdata/corpus --truth testdata/corpus-truth.json
```

**Das Ergebnis vom 06.09.2026: null Fehler** über sechs Seiten und 3.148 Zeichen,
in allen drei Varianten, einschließlich der Großumlaute, des Schweizer
Apostrophs in `CHF 1'234.56`, des Betrags `1.234,56 Euro`, beider Datumsformate
und des Aktenzeichens mit Schrägstrichen. Der ganze Lauf, die Kommandozeile, drei
Gegenproben und der Abschnitt, was die Zahl nicht sagt, stehen in
`docs/measurements/2026-09-06-ocr-dach/README.md`.

Das Werkzeug trägt einen **groben** Riegel, 0,05, und die Grobheit ist der Punkt.
Er fängt einen Totalausfall, eine Seite, die leer oder als Rauschen zurückkommt.
Er fängt ausdrücklich nicht eine falsch gewählte Sprache: gemessen liest `eng`
allein dieselben Seiten mit 0,0203 und `fra` allein mit 0,0073, beides weit unter
dem Riegel. Eine Grenze, die das fangen würde, wäre die scharfe Grenze, die
dieser Abschnitt oben aus guten Gründen ablehnt. Die falsche Sprache wird
stattdessen von der Positivliste in `findling.config` und vom Bau des Abbilds
abgefangen, der ohne `deu`, `eng` und `fra` in `--list-langs` gar nicht
entsteht.

### Die Fraktur-Option: dokumentiert, ausdrücklich kein Standard

Für Frakturschrift gibt es in Debian trixie Sprachdaten, und der Auftrag zu D-09
verlangt dafür eine dokumentierte Option und keinen Standard. Genau so steht es
im Abbild: der Eintrag in `backend/Dockerfile` ist auskommentiert, und
einschalten heißt, die Zeile freizulegen **und** `frk` in die Positivliste von
`backend/src/findling/config.py` aufzunehmen. Beides, nicht eines von beidem,
sonst filtert die Positivliste die Sprache wieder weg.

Die Paketlage, geprüft am 06.09.2026:

| Sprachkennung | Paket in trixie | Stand |
|---|---|---|
| `frk` | `tesseract-ocr-frk` 1:4.1.0-2 | existiert, "language files for German (Fraktur)" |
| `frk` (Skriptdaten) | `tesseract-ocr-script-frak` 1:4.1.0-2 | existiert ebenfalls |
| `deu_frak` | `tesseract-ocr-deu-frak` | existiert **nicht**, "No such package" |
| `deu_latf` | kein Paket | stromaufwärts die neue Kennung, siehe unten |

Die Umbenennung ist der Satz, der einen späteren Leser sonst eine Stunde kostet:
stromaufwärts ist `frk` in `deu_latf` umbenannt und die Nutzung von `frk` gilt
als überholt. Die Debian-Sprachdaten stehen aber weiterhin auf 4.1.0 und führen
`frk`. Wer nach `deu_latf` sucht, findet in trixie nichts, und wer daraus
schließt, Fraktur sei nicht verfügbar, schließt falsch.

Gemessen ist Fraktur nicht. Es liegt keine gerenderte Frakturseite im Korpus,
und der Bericht vom 06.09.2026 sagt zu Fraktur ausdrücklich nichts.

## Was diese Seite nicht misst

Ehrlichkeitshalber, damit die nächste Phase nicht das Falsche annimmt:

- **Die OCR-Qualität auf echten Scans.** Die Vorlage hier ist gerenderter Text,
  also der freundlichste denkbare Fall. Wie gut tesseract ein schief
  eingescanntes Protokoll liest, sagt diese Seite nicht, und der Abnahmetest für
  D-09 prüft es bewusst über auffindbare Suchbegriffe statt über einen
  Rohtextvergleich.
- **ARM-Laufzeit.** Alle Zeitwerte stammen von amd64. Die Sprachdaten sind
  `Architecture: all` und damit bitgleich, der Adressraumbedarf hängt an der
  Pixelzahl, aber die Sekunden je Seite gelten auf einer ARM-Box nicht.

Was für arm64 dagegen sehr wohl geprüft ist, ist die Paketauflösung, denn dort
sitzt das eigentliche Risiko der Versions-Pins:

```
docker run --rm --platform linux/arm64 python:3.13-slim-trixie@sha256:ffb752e1... \
    apt-get install -s -y --no-install-recommends tesseract-ocr \
        tesseract-ocr-deu=1:4.1.0-2 tesseract-ocr-eng=1:4.1.0-2 tesseract-ocr-osd=1:4.1.0-2
# Inst libtesseract5     (5.5.0-1+b1 Debian:13.6/stable [arm64])
# Inst tesseract-ocr     (5.5.0-1+b1 Debian:13.6/stable [arm64])
# Inst tesseract-ocr-deu (1:4.1.0-2  Debian:13.6/stable [all])
# Inst tesseract-ocr-eng (1:4.1.0-2  Debian:13.6/stable [all])
# Inst tesseract-ocr-osd (1:4.1.0-2  Debian:13.6/stable [all])
```

Zwei Dinge stehen damit fest. Die drei harten Pins auf `1:4.1.0-2` lösen auf
arm64 genauso auf wie auf amd64, weil die Pakete `Architecture: all` sind. Und
die Engine trägt auf beiden Architekturen die Binary-NMU-Version `5.5.0-1+b1`,
nicht `5.5.0-1`: ein harter Pin auf die in der Recherche genannte Version hätte
also nicht nur den arm64-Bau gebrochen, sondern beide. Das ist der Beleg für die
Entscheidung im Dockerfile, die Engine ungepinnt zu lassen und stattdessen am
Digest des Basis-Image zu verankern.

## Reproduzieren

Der zusätzliche Kontext `scripts` ist seit Phase 6 nötig: die Modellstufe des
Dockerfiles ruft `scripts/dev/quantize_model.py`, und diese Datei liegt
außerhalb des Bau-Kontextes `backend`.

```
docker build --build-context scripts=./scripts -f backend/Dockerfile -t findling-ocr-check backend
docker run --rm --entrypoint tesseract findling-ocr-check --list-langs
docker run --rm --entrypoint sh findling-ocr-check \
    -c 'test -s /usr/local/share/findling/COPYING.tesseract'
```

Der Messtreiber selbst liegt bewusst nicht im Repository: er baut eine
Wegwerf-PDF und ruft die oben abgedruckten Kommandozeilen auf, und jede davon
steht in dieser Datei vollständig genug, um sie einzeln nachzustellen. Was
dauerhaft geprüft werden muss, prüft stattdessen der Bau selbst, fail closed:
ohne `deu` und `eng` in `--list-langs` und ohne beide Lizenztexte entsteht gar
kein Image.
