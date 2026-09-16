# Stereo-Vision-Lokalisierung

Semesterprojekt Elektrotechnik (HTW Berlin, SoSe 2026, Betreuer: Prof.
Steffen Borchers-Tigasson). Grundlage für spätere Rover-Navigation im
Rahmen der [European Rover Challenge](https://roverchallenge.eu/). Ziel
ist eine schriftliche Arbeit + Code, **kein** Demo/Präsentation. Scope:
prototypische Umsetzung / Proof-of-Concept, kein Produktionscode.

## Worum geht es

Ein Stereo-Kamerasystem bestimmt seine eigene Position und Orientierung in
einem Innenraum (Testbereich ca. 10×10 m) — ausschließlich anhand
natürlicher Objekte im Raum, **ohne** künstliche Marker (kein ArUco).

**Ansatz: einfache Visuelle Odometrie (VO) ohne Loop-Closure.** Statt
gegen ein vorher vermessenes Set an Referenzpunkten zu lokalisieren
(map-based), wird die Kamerabewegung schrittweise aus zeitlichem
Feature-Matching (Frame *t-1* ↔ Frame *t*) und Stereo-Triangulation
geschätzt und zu einer Trajektorie aufsummiert — verankert an einem
einmalig vermessenen Startpunkt. Kein Kartenaufbau, keine
Wiedererkennungs-/Korrekturlogik. Motivation: realistischer für ein
Rover-Szenario, das eine unbekannte Umgebung nicht vorher von Hand
vermessen kann. Volles SLAM (Loop-Closure, Bundle Adjustment) bleibt
konzeptioneller Ausblick, ist aber nicht implementiert — Drift über die
Strecke ist eine bekannte, in der Arbeit offen diskutierte Einschränkung
(Metriken: ATE/RPE). Details und Alternativenabwägung siehe
[`docs/decisions.md`](docs/decisions.md).

## Pipeline

```
Stereo-Kalibrierung          Visuelle Odometrie (pro Frame-Paar)
─────────────────────        ──────────────────────────────────
Schachbrett-Aufnahmen   →    Feature-Detektion (ORB)
  ↓ calibrateCamera           ↓
Intrinsics (je Kamera)       Stereo-Matching + Triangulation → 3D-Punkte
  ↓ stereoCalibrate            ↓
Extrinsics (Baseline,        Zeitliches Matching zu Frame t-1
  Rotation/Translation)        ↓ (Lowe's Ratio-Test)
  ↓ stereoRectify             Kabsch-Alignment + RANSAC → relative Pose
Rektifizierung (P1, P2)   →   ↓
                              Posen-Verkettung → Trajektorie
```

Reine Berechnungslogik (`src/`) ist strikt von Kamera-I/O getrennt und
läuft ohne angeschlossene Kamera testbar über `pytest`.

## Hardware

- **Raspberry Pi 4B** — primäre Entwicklungs- und Zielplattform
- **Arducam B0266 Stereo-Kit**: 2× OV9281 Global-Shutter-Sensoren,
  Camarray-HAT, CSI, hardware-synchronisiert, Baseline ~60 mm
- **Jetson Nano** — spätere Portierung, im Rahmen des Rover-Projekts
- Zielarbeitsbereich: 0,3–2 m Entfernung
- Kamera bewegt sich zwischen Aufnahmen (nötig für VO), steht aber
  während jeder einzelnen Aufnahme still (Stop-and-Shoot,
  Global-Shutter-Sensoren) — kein Rolling-Shutter-/Bewegungsunschärfe-
  Problem pro Einzelbild
- Ground Truth für Validierung: Maßband (PoC-Niveau)

## Was explizit nicht Teil des Projekts ist

- Keine ROS2-Integration selbst — Code ist nur strukturell so gebaut,
  dass ein späterer ROS2-Wrapper leicht möglich ist
- Kein ArUco-/Marker-basierter Ansatz
- Kein vollständiges SLAM (Loop-Closure, Bundle Adjustment, persistente
  Karte) — nur einfache VO ohne diese Korrekturmechanismen

## Projektphasen

1. **Kalibrierung** — intrinsisch/extrinsisch, Rektifizierung, erste
   Tiefenmessung vs. Maßband
2. **Lokalisierungsalgorithmus (VO)** — Feature-Detektion, 3D-Position via
   Stereo-Disparität, zeitliches Matching, Posen-Verkettung
3. **Validierung** — systematische Messreihen, Trajektorien-Fehlermetriken
   (ATE/RPE) gegen Maßband-Ground-Truth
4. **Ausblick** — volles SLAM als konzeptionelle Erweiterung, nicht
   implementiert

Der aktuelle Stand und Fortschritt pro Arbeitstag steht in
[`docs/daily-log.md`](docs/daily-log.md) und
[`CHECKLIST.md`](CHECKLIST.md), Begründungen einzelner Entscheidungen in
[`docs/decisions.md`](docs/decisions.md).

## Repo-Struktur

```
et-projekt/
  src/
    calibration/   # Intrinsic/Extrinsic-Kalibrierung, Rektifizierung
    capture/       # Kamera-I/O, synchronisierte Bildaufnahme
    localization/  # Feature-Detektion, Disparität, Pose-Schätzung, VO
    evaluation/    # Messreihen, Fehlermetriken (ATE/RPE)
  tests/           # pytest, reine Logik ohne laufende Kamera testbar
  scripts/         # visuelle Sanity-Check- & Orchestrator-Skripte
  data/            # Kalibrier-/VO-Aufnahmen + Ground-Truth-Wegpunkte
  results/         # Kalibrierergebnisse & Messreihen, versioniert mit Datum
  docs/            # Entscheidungs-Log, Daily Log
```

## Setup & Nutzung

```bash
python3 -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt

pytest                              # Unit-Tests (ohne Kamera)
python scripts/run_calibration.py   # Kalibrier-Pipeline auf Aufnahmen in data/
python scripts/run_vo_sequence.py   # VO-Pipeline auf einer Bildsequenz
```

Die `scripts/check_*.py`-Skripte sind visuelle Sanity-Checks (Reprojection-
Error-Plot, rektifizierte Bilder, Disparitätskarte, Feature-Matches, …) —
getrennt von den automatisierten Tests, weil viele CV-Fehler nur visuell
auffallen.

## Kontext

Grundlage für spätere Rover-Navigation im Rahmen der European Rover
Challenge — dieses Projekt liefert das Vision-Modul zur
Selbstlokalisierung, ROS2-Integration und mobiler Einsatz sind spätere
Schritte außerhalb dieses Semesterprojekts.
