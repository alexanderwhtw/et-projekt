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
