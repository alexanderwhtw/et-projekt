# Entscheidungs-Log

Kurze Einträge zu nicht-trivialen Entscheidungen im Projekt (Algorithmus-
Wahl, Schwellwerte, Architektur-Entscheidungen). Dient auch als Grundlage
für die schriftliche Arbeit.

## Format

**YYYY-MM-DD** — Kurztitel der Entscheidung

- Kontext:
- Alternativen:
- Begründung:

## 2026-09-02 — Manuelle Belichtung statt Auto-Exposure für Kalibrieraufnahmen

- Kontext: Kalibrieraufnahmen (Schachbrett, mehrere Aufnahmen über Zeit)
  brauchen konstante Belichtung; Auto-Exposure würde zwischen Frames
  driften. 5 Testaufnahmen mit `rpicam-still` (verschiedene Shutter/Gain/
  AWB-Kombinationen) ausgewertet, Details in `cal/opt_calib.md` (Ordner
  `cal/` ist gitignored — Ad-hoc-Testbilder, nicht die finale
  Kalibrier-Datenbasis).
- Alternativen: Auto-Exposure/Auto-Gain belassen; feste Werte nur pauschal
  raten ohne Messung.
- Begründung: Manuelle Werte (`--shutter --gain`) machen Aufnahmen
  reproduzierbar. Kandidatenwerte für die Testszene: `--shutter 3500
  --gain 1.0 --awbgains 1.0,1.0 --denoise off` (Startpunkt, muss mit
  echtem Schachbrett-Motiv wegen hellerer Reflexion nachjustiert werden).
  AWB fix auf (1.0, 1.0), da Sensor Mono ist (kein Farbbild, AWB
  irrelevant). Denoise aus, um Schachbrett-Ecken nicht zu glätten.
- Nebenbefund: Linker und rechter Kanal sind systematisch ~5,5–7,5 %
  unterschiedlich hell (reproduzierbar über alle 5 Durchläufe, nicht durch
  Szeneninhalt erklärbar, nicht durch AWB/CCM verursacht — vermutlich
  Sensor-/Objektiv-Unterschied). Für Phase 2 (Feature-Matching) vermutlich
  unkritisch, für dichtes Stereo-Matching ggf. Helligkeitsnormalisierung
  als Preprocessing-Schritt in `src/capture` vormerken — keine Entscheidung
  heute nötig, nur Beobachtung.

## 2026-09-02 — Baseline (Stereo-Basisbreite) gemessen: 60 mm

- Kontext: Abstand der beiden Linsenmittelpunkte (Arducam B0266 Stereo-Kit)
  mit Maßband nachgemessen.
- Wert: **60 mm**.
- Verwendungszweck: Referenzwert für Plausibilitätscheck der Translation
  (`T`) aus `cv2.stereoCalibrate` in Phase 1 — der berechnete Baseline-Wert
  sollte nahe an dieser manuell gemessenen Distanz liegen. Maßband-Messung
  ist PoC-Niveau (siehe CLAUDE.md), keine hochpräzise Referenz.

## 2026-09-02 — Roll-Verkippung (~2,25°) akzeptiert, kein mechanischer Fix im Prototyp

- Kontext: Level-Check (Testaufnahme, ORB-Feature-Matching zwischen L/R +
  RANSAC-Fit von `dy = a + b*(x - cx)`, Skript `cal/analyze_roll.py`)
  zeigt eine Roll-Verkippung zwischen den beiden Kameras: Steigung
  b ≈ 0,0393 → Roll-Winkel ≈ 2,25°, plus konstanter vertikaler Versatz
  a ≈ 6,8 px am Bildzentrum (130 von 139 Matches als RANSAC-Inlier). Über
  die volle Bildbreite ergibt sich eine vertikale Streuung von ca. 22 px
  (~2,7 % der Bildhöhe von 800 px).
- Ursache: aktueller Prototyp-Aufbau fixiert die Kamera nur mit Nägeln,
  keine präzise Halterung — Verkippung war erwartet.
- Alternativen: Mechanische Nachjustage jetzt vs. Verkippung akzeptieren
  und softwareseitig (stereoRectify) korrigieren lassen.
- Begründung: Für den prototypischen Aufbau (PoC, kein Produktionscode,
  siehe CLAUDE.md) wird die Verkippung akzeptiert — `stereoRectify`
  korrigiert das rechnerisch, kostet aber ca. 2–3 % Bildbereich am Rand.
  Kein Blocker für Phase 1. Bei einer stabileren Halterung (spätere
  Iteration/Rover-Integration) sollte der Wert erneut geprüft werden, da
  eine geringere Verkippung mehr nutzbaren Bildbereich nach der
  Rektifizierung übrig lässt.

## 2026-09-02 — Hardware-Synchronisation L/R verifiziert (Stoppuhr-Test)

- Kontext: Tag-1-Sync-Test war nur qualitativ ("beide Kameras liefern
  synchrones Bild"). Verschärfter Test: Handy mit laufender Stoppuhr
  (Hundertstelsekunden-Anzeige) im Abstand von ca. 50 cm vor der Kamera
  positioniert, ein Still (2560x800) aufgenommen, L- und R-Bildhälfte
  digit-genau verglichen.
- Ergebnis: Beide Hälften zeigen identisch **02:59,34** — kein Zeitversatz
  erkennbar. Bild: `cal/bilder/synctest_zoom_compare.png` (gitignored).
- Zusätzliche Architektur-Begründung: `rpicam-still --list-cameras` zeigt
  nur **ein** Kamera-Device (`arducam-pivariety`), nicht zwei separate
  Streams; Metadata eines Captures enthält nur **einen** `SensorTimestamp`
  fürs komplette Frame. Das Camarray-HAT liefert L+R also als einen
  gemeinsamen, hardware-synchronisierten Ausleseprozess, kein
  nachträgliches Software-Stitching zweier unabhängiger Kameras — ein
  unabhängiger Zeitversatz zwischen L/R ist architektonisch praktisch
  ausgeschlossen.
- Einschränkung: Auflösungsgrenze der Methode liegt bei ~10ms (Hundertstel-
  Digit-Wechsel der Stoppuhr-App). Ein Sub-Millisekunden-Versatz wäre damit
  nicht nachweisbar, ist aber für Phase 1/2 (Feature-Matching, Pose bei
  ruhender Kamera) irrelevant, da die Kamera während der Messung ohnehin
  fest steht (kein Rolling-Shutter-/Bewegungsproblem, siehe CLAUDE.md).

## 2026-09-03 — Belichtung ist sitzungsabhängig, nicht fest verdrahten

- Kontext: Erste Schachbrett-Testaufnahme (1m, frontal) mit dem Tag-2-
  Kandidaten `--shutter 3500 --gain 1.0` ergab ein deutlich unterbelichtetes
  Bild (weiße Felder nur ~mittelgrau, max=100 statt >200 in der
  Board-Region) — Board stand im Schatten, während die Auto-Metering-
  Referenz von Tag 2 einen helleren, fensternahen Bereich der Szene traf.
  Ecken wurden dadurch nicht erkannt.
- Ergebnis: Mit `--shutter 10000 --gain 1.0 --awbgains 1.0,1.0 --denoise off`
  (statt 3500) alle 49 Innenecken (7x7) in L und R zuverlässig erkannt.
- Begründung/Konsequenz: Lux/Lichtverhältnisse schwanken spürbar zwischen
  Sitzungen (Tageszeit, Bewölkung, Objektposition relativ zum Fenster).
  Ein einmalig ermittelter Belichtungswert taugt nicht als dauerhafte
  Konstante — vor jeder Aufnahmeserie kurz mit `cv2.findChessboardCorners`
  gegenchecken, ob die Ecken erkannt werden, statt blind einen alten Wert
  zu übernehmen. Für die spätere `src/capture`-Implementierung: entweder
  Belichtung pro Session neu kalibrieren (kurzer Auto-Messdurchlauf, dann
  fixieren) oder mit etwas mehr Sicherheitsabstand nach oben arbeiten.

## 2026-09-03 — Schachbrett muss asymmetrisch sein (7x7 verursacht Ecken-Vertauschung)

- Kontext: Beim ersten Eckenerkennungs-Test (Board 1m, frontal, 8x8 Felder
  = 7x7 Innenecken) zeigte die Visualisierung (`cv2.drawChessboardCorners`)
  in L und R einen **entgegengesetzten** Farbverlauf der Punktreihenfolge.
  Nachgerechnet: `L[0]` ≈ (703.6, 493.5) liegt an (fast) derselben
  physischen Ecke wie `R[-1]` ≈ (651.6, 501.6) — die Punktlisten sind also
  zwischen L und R komplett gegenläufig indiziert.
- Ursache: 7x7 ist ein symmetrisches Muster (gleiche Zeilen-/Spaltenzahl).
  `cv2.findChessboardCorners` legt die Scan-Startecke/-Richtung anhand
  lokaler Bildmerkmale fest, nicht anhand einer global eindeutigen
  Markierung — bei einem symmetrischen Muster kann diese Wahl zwischen zwei
  Aufnahmen (hier: L vs. R desselben Frames) unterschiedlich ausfallen,
  ohne dass sich die Kamera/das Board tatsächlich gedreht hat.
- Alternativen: (a) Reihenfolge nachträglich im Code heuristisch angleichen
  (z.B. per Positions-/Abstandsvergleich zwischen erster/letzter Ecke L↔R
  umsortieren), (b) neues asymmetrisches Muster drucken (z.B. 9x6
  Innenecken).
- Begründung: (b) gewählt für den finalen Kalibrier-Datensatz — vermeidet
  die Fehlerquelle strukturell statt mit fragiler Heuristik, die bei jeder
  neuen Pose erneut greifen müsste und schwer zu testen ist. Für die
  heutigen Sanity-Checks (Belichtung, Verzeichnung, reine
  Erkennbarkeitsprüfung) bleibt das vorhandene 7x7-Muster nutzbar, da dort
  keine L/R-Punktkorrespondenz gebraucht wird. Vor der eigentlichen
  `stereoCalibrate`-Datenaufnahme: neues Muster (9x6, ausgemessen, mit
  weißem Rand) drucken.

## 2026-09-03 — Verzeichnung & L/R-Helligkeit über 3 Board-Posen quantifiziert

- Kontext: 3 Testaufnahmen mit dem 7x7-Schachbrett bei `--shutter 10000
  --gain 1.0 --awbgains 1.0,1.0 --denoise off`: (1) 1m, frontal/mittig,
  (2) Ecke oben-links, leicht gekippt, (3) weit rechts, nah am Bildrand,
  stark gekippt. Alle Ecken via `cv2.findChessboardCornersSB` erkannt.
- Verzeichnung: Für jede der 7 Ecken-Reihen eine Gerade gefittet (Total-
  Least-Squares) und die maximale senkrechte Abweichung der 7 Punkte davon
  gemessen (physische Reihen sind exakt gerade, Abweichung im Bild = Indiz
  für Linsenverzeichnung). Ergebnis: 0,11px (Pose 1) / 0,27px (Pose 2) /
  0,37px (Pose 3, am nächsten zum Bildrand) — durchgängig sehr klein.
  Einschränkung: keine der Posen lag exakt in der äußersten Bildecke, für
  eine vollständige Verzeichnungs-Charakterisierung (relevant für die
  radialen Distortion-Koeffizienten in `calibrateCamera`) reicht das nicht,
  ist aber ein positives erstes Signal (Objektiv scheint wenig verzeichnet).
- L/R-Helligkeit: Mittelwert-Differenz nur auf der Board-Bounding-Box (statt
  ganzes Bild wie in Tag 2): 1,2 % / 1,2 % / 2,9 % über die 3 Posen — klar
  kleiner als der ~6 % Szenen-Unterschied aus Tag 2. Erklärung: dort wurde
  die gesamte, unterschiedlich beleuchtete Szene verglichen; hier ein
  kleiner Bildausschnitt mit nahezu identischem Inhalt in L/R. Für Phase 2
  (Feature-Matching) unkritisch.
- Nebenbefund (technisch, relevant für `src/calibration`):
  `cv2.CALIB_CB_FAST_CHECK` lehnte Pose 3 (großes, stark gekipptes Brett)
  faelschlich ab (falsches Negativ) — ohne das Flag bzw. mit
  `cv2.findChessboardCornersSB(..., flags=cv2.CALIB_CB_EXHAUSTIVE)`
  zuverlässig erkannt. Für die spätere Kalibrier-Implementierung
  `findChessboardCornersSB` ohne `FAST_CHECK` verwenden, siehe
  `cal/check_corners.py` als Referenzimplementierung.

## 2026-09-03 — Schachbrett auch bei ~2m Distanz noch erkennbar

- Kontext: 4. Testpose bei ca. 2m Distanz (obere Grenze des Zielarbeits-
  bereichs, siehe CLAUDE.md), frontal. Alle 49 Ecken in L und R erkannt,
  Reihenfolge zwischen L/R konsistent.
- Messung: Board (7x7 Innenecken) nur noch ~63x62px groß im Bild, das
  entspricht ~10,5px pro Feld (bei 24mm realer Feldkantenlänge).
- Einschätzung: Erkennung funktioniert trotz geringer Pixelgröße
  zuverlässig, aber die Subpixel-Genauigkeit der Eckenlokalisierung dürfte
  bei so wenigen Pixeln/Feld geringer sein als bei näheren Distanzen —
  keine Präzisionsmessung dazu gemacht, nur Plausibilitätsprüfung. Für
  PoC-Niveau (siehe CLAUDE.md) ausreichend; bei der finalen
  Kalibrierdatensammlung ggf. mehr Aufnahmen im Nah-/Mittelbereich
  gewichten und Fernbereich (~2m) nicht übergewichten, da unpräziser.
- Noch offen: Nahbereich (~0,3m) nicht getestet.
