# Daily Log

Kurzes Stichpunkt-Protokoll der Arbeitssitzungen (ergänzt die Checklist um
Kontext/Details, siehe auch `docs/decisions.md` für Begründungen einzelner
Entscheidungen).

## 2026-09-01 (Tag 1)

- SSH-Verbindung zum Pi geprüft: `rasp-local` (`raspberrypi.local`)
  funktioniert, `rasp-lan` (statische IP im lokalen Heimnetz, siehe lokale
  SSH-Config) aktuell nicht erreichbar (Timeout)
- IPA-Tuning-Problem analysiert und behoben: Arducam-Pivariety-Treiber
  meldet Kameranamen generisch als `arducam-pivariety` statt `ov9281`,
  libcamera fand daher keine Tuning-Datei für AE/AWB. Fix: Symlink
  `arducam-pivariety_mono.json` → `ov9281_mono.json` in
  `/usr/share/libcamera/ipa/rpi/vc4/` angelegt, mit `rpicam-still`
  verifiziert
- VS Code auf dem Mac aktualisiert: alte, unverwaltete Kopie (1.73.0) lag
  in `~/Downloads`; über Homebrew Cask neu installiert (1.135.0) nach
  `/Applications`, alte Kopie gelöscht
- Repo-Grundgerüst gemäß `CLAUDE.md`-Struktur angelegt: `src/{calibration,
  capture, localization, evaluation}`, `tests/`, `scripts/` (Stubs für
  `check_calibration.py`, `check_rectification.py`, `check_disparity.py`),
  `data/`, `results/{calibration,measurements}`, `docs/`,
  `requirements.txt`, `pytest.ini`
- Stray leere Datei `projekt` (Tippfehler-Überbleibsel) entfernt
- Alles committet und nach `origin/main` gepusht

## 2026-09-02 (Tag 2)

Vorbereitung Kalibrierung: Kamera-Settings & Sanity-Checks vor dem
eigentlichen Kalibrier-Code (Phase 1). Ad-hoc-Testbilder/-Skripte liegen in
`cal/` (gitignored, nicht Teil der finalen Kalibrier-Datenbasis).

- **Kamera-Settings**: 5 Testaufnahmen mit `rpicam-still` durchgespielt
  (Auto vs. manuelle Shutter/Gain-Werte, AWB/Denoise-Varianten), ausgewertet
  mit `cal/analyze_capture.py` (Helligkeits-Stats pro Bildhälfte,
  annotierte L/R-Vergleichsbilder). Kandidatenwerte für Kalibrieraufnahmen:
  `--shutter 3500 --gain 1.0 --awbgains 1.0,1.0 --denoise off`. Nebenbefund:
  linker Kanal systematisch ~5,5–7,5 % heller als rechter, reproduzierbar
  über alle Durchläufe, Ursache vermutlich Sensor-/Objektiv-Unterschied
  (nicht AWB/CCM). Details: `docs/decisions.md`, `cal/opt_calib.md`.
- **Level-Check (Roll)**: quantifiziert per ORB-Feature-Matching + RANSAC
  (`cal/analyze_roll.py`) statt nur visuell — Roll ≈ 2,25°, vertikaler
  Versatz ~6,8px am Bildzentrum. Erwartungsgemäß spürbar, da Kamera aktuell
  nur mit Nägeln fixiert ist; für den Prototyp akzeptiert, `stereoRectify`
  korrigiert das später.
- **Baseline** (Linsenmittelpunkt zu Linsenmittelpunkt) mit Maßband
  nachgemessen: 60mm.
- **Stabilität & CSI-Kabel** geprüft, unauffällig (Kamera steht auf festem
  Tisch).
- **Synchronisation** verschärft getestet: Stoppuhr (Hundertstelsekunden)
  auf Handy-Display in 50cm Abstand fotografiert, L/R zeigen identisch
  02:59,34 — kein Zeitversatz messbar. Zusätzlich Architektur-Check: nur
  ein Kamera-Device (`arducam-pivariety`), ein `SensorTimestamp` pro Frame
  → Zeitversatz zwischen L/R architektonisch praktisch ausgeschlossen.
- Restliche Punkte aus der Tag-2-Checkliste (Fokus mechanisch fixieren,
  Schachbrett vorbereiten, Testaufnahmen mit Schachbrett-Motiv,
  Verzeichnungsprüfung) nicht mehr geschafft, verschoben auf Tag 3 (siehe
  `CHECKLIST.md`).
- Ordner `cal/` (Testbilder/-skripte für die Settings-Optimierung) ins
  Repo-Root verschoben und in `.gitignore` aufgenommen (Wunsch: Bilder im
  Projektordner statt an anderer Stelle auf dem Mac, aber nicht in der
  Git-Historie).

## 2026-09-03 (Tag 3)

Erstes Schachbrett gedruckt (8×8 Felder, 24mm Kantenlänge, DIN A4,
online gefundenes Muster) und für Testzwecke an einer Stuhllehne
positioniert. Vier Testaufnahmen in verschiedenen Posen, ausgewertet mit
neuen Skripten `cal/check_corners.py` (Ecken-Erkennung via
`cv2.findChessboardCornersSB`) — alle 49 Ecken (7×7 Innenecken) in jeder
Pose in L und R gefunden.

- Belichtung von Tag 2 (`--shutter 3500`) reichte bei den heutigen
  (dunkleren) Lichtverhältnissen nicht — Board lag im Schatten, Ecken
  nicht erkennbar. Neuer Kandidat: `--shutter 10000 --gain 1.0
  --awbgains 1.0,1.0 --denoise off`. Erkenntnis: Belichtung ist
  sitzungsabhängig, nicht projektweit fest verdrahten.
- **Wichtiger Befund**: Das 8×8-Muster (7×7 Innenecken, symmetrisch)
  erzeugt eine empirisch bestätigte Ecken-Reihenfolge-Mehrdeutigkeit
  zwischen L/R (`cv2.findChessboardCorners` liefert die Punktliste teils
  gegenläufig sortiert). Für die heutigen Sanity-Checks unproblematisch,
  für `stereoCalibrate` aber blockierend — neues asymmetrisches Muster
  (z.B. 9×6) muss vor der echten Kalibrier-Datenaufnahme gedruckt werden.
- Verzeichnungsprüfung (Zeilen-Geraden-Abweichung der erkannten Ecken):
  max. 0,37px selbst nah am Bildrand → Objektiv scheint wenig verzeichnet,
  aber noch nicht in der äußersten Bildecke getestet.
- L/R-Helligkeitsunterschied auf der Board-Fläche selbst nur 1,2–2,9 %,
  deutlich kleiner als der Szenen-Unterschied aus Tag 2 (~6 %) — plausibel,
  da hier nahezu identischer Bildinhalt verglichen wird.
- Bei ~2m Distanz (obere Grenze des Zielarbeitsbereichs) nur noch
  ~10,5px pro Feld im Bild, Ecken trotzdem zuverlässig erkannt.
- Technischer Nebenbefund: `cv2.CALIB_CB_FAST_CHECK` lehnt große/stark
  gekippte Bretter fälschlich ab — `findChessboardCornersSB` ohne dieses
  Flag verwenden (relevant für spätere `src/calibration`-Implementierung).
- Nicht mehr geschafft (→ Tag 4): Fokus mechanisch fixieren, neues
  asymmetrisches Muster drucken, Schachbrett fest montieren, Quadratgröße
  nachmessen, gezielte Beleuchtungsprüfung, Nahbereich-Testaufnahme
  (~0,3m), Namenskonvention für `data/calibration_images/`.

## 2026-09-04 (Tag 4)

Statt eines neuen 9×6-Musters wurde das vorhandene 8×8-Feld-Schachbrett um
eine äußere Feldreihe beschnitten (→ 6×7 Innenecken, asymmetrisch) und auf
eine Kartonplatte geklebt, an der Stuhllehne befestigt. Namenskonvention
für `data/calibration_images/` festgelegt (`left_NNN.png`/`right_NNN.png`
+ `manifest.csv`), Details siehe `docs/decisions.md`.

- Testaufnahme vom Pi geholt und ausgewertet: `findChessboardCornersSB`
  findet 7×7 nicht mehr, 6×7 zuverlässig und mit konsistenter
  Eckreihenfolge in L/R — Zuschnitt hat den Tag-3-Bug behoben. L/R-
  Helligkeit auf der Board-Fläche fast identisch (94,4 vs. 93,7, ≈0,7 %).
  Board stand in diesem Test spürbar nicht-frontal zur Kamera (deutliche
  Foreshortening in x vs. y) — für künftige Aufnahmen auch eine frontale
  Pose einplanen.
- Fokus: keine manuell zugängliche Einstellmöglichkeit am Kameramodul
  gefunden — Punkt als nicht-aktionabel akzeptiert, nichts zu fixieren.
- Quadratgröße mit Messschieber/Lineal nachgemessen: 24mm bestätigt.
- Nahbereichstest (~0,3m) verschoben — aktueller Prototyp-Aufbau lässt
  sich nicht ohne größeren Umbau dafür anpassen.
- Beleuchtungsprüfung zurückgestellt.
- Projekt-Prinzip festgelegt: erst eine durchgängig funktionierende
  Pipeline bauen (auch mit bekannten Ungenauigkeiten in Mechanik/
  Beleuchtung/Fokus), Fine-Tuning/Exaktheit erst in einer späteren Phase.
  Details siehe `docs/decisions.md`.
- Damit ist Tag 4 inhaltlich abgeschlossen — nächster Schritt: Beginn der
  eigentlichen `src/calibration`-Implementierung (Phase 1).

**Nachtrag, selber Tag — Grundsatz-Methodenwechsel:** Beim Vorbereiten der
Referenzpunkt-Vermessung wurde der ursprüngliche map-based Ansatz nochmal
hinterfragt (weniger Zeit als angenommen + Realismus-Argument: ein echter
Rover kann eine neue Umgebung nicht vorher von Hand vermessen). Ergebnis:
Wechsel zu einfacher Visueller Odometrie (VO) ohne Loop-Closure — Details,
Alternativenabwägung und Konsequenzen in `docs/decisions.md`. `CLAUDE.md`,
`projektbrief.md` und `data/reference_points.yaml` entsprechend
aktualisiert. Diese Entscheidung weicht vom ursprünglichen, mit
Betreuer-Kontext dokumentierten Projektbrief ab — sollte bei Gelegenheit
mit Prof. Borchers-Tigasson rückgespiegelt werden. Referenzpunkt-Aufgabe
ist dadurch nicht komplett entfallen, sondern kleiner geworden: nur noch
ein Startpunkt-Ursprung nötig statt mehrerer Landmarken.
