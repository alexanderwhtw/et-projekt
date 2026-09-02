# Daily Log

Kurzes Stichpunkt-Protokoll der Arbeitssitzungen (ergänzt die Checklist um
Kontext/Details, siehe auch `docs/decisions.md` für Begründungen einzelner
Entscheidungen).

## 2026-09-01 (Tag 1)

- SSH-Verbindung zum Pi geprüft: `rasp-local` (`raspberrypi.local`)
  funktioniert, `rasp-lan` (statische IP `192.168.50.2`) aktuell nicht
  erreichbar (Timeout)
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
