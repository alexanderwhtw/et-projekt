# ET-Projekt: Stereo-Vision-Lokalisierung

Semesterprojekt Elektrotechnik (HTW Berlin, SoSe 2026, Betreuer: Prof. Steffen
Borchers-Tigasson). Grundlage für spätere Rover-Navigation (European Rover
Challenge). Ziel: schriftliche Arbeit + Code, **kein** Demo/Präsentation nötig.
Scope: prototypische Umsetzung / Proof-of-Concept, kein Produktionscode.

## Ziel

Ein Stereo-Kamerasystem bestimmt seine Position + Orientierung in einem
definierten Testbereich (Innenraum ~10×10m) anhand natürlicher Objekte im
Raum. Kein ArUco, kein SLAM (nur als Ausblick erwähnt, nicht implementiert).
Ansatz: **map-based** — vorher vermessene Referenzpunkte im Testraum, Pose
wird relativ dazu bestimmt.

## Hardware

- Raspberry Pi 4B — primäre Entwicklungsplattform (Ziel: Entwicklung direkt
  auf dem Pi via VS Code Remote-SSH, nicht auf dem Host-Rechner)
- Arducam B0266 Stereo-Kit: 2× OV9281 Global-Shutter, Camarray-HAT, CSI,
  hardware-synchronisiert
- Jetson Nano (später, Portierung, Modell noch offen)
- Kamera steht fest während Messung (kein Rolling-Shutter-Problem)
- Zielbereich: 0,3–2m (kleine Baseline des Kits)
- Ground Truth für Validierung: Maßband (PoC-Niveau reicht, keine
  hochpräzise Referenzmessung nötig)

## Nicht Teil des Projekts (explizit ausklammern)

- Keine ROS2-Integration selbst — Code soll nur **strukturell** so gebaut
  sein, dass ein späterer ROS2-Wrapper leicht möglich ist (klare Trennung
  Logik/I/O). Kein ROS2-Setup, keine ROS2-Nodes jetzt schreiben.
- Kein ArUco/Marker-basierter Ansatz (weder primär noch als Cross-Validation)
- Kein SLAM/visuelle Odometrie als Implementierung (nur Konzept im Ausblick)

## Roadmap / Phasen

1. **Kalibrierung** — intrinsisch (Schachbrett, je Kamera), extrinsisch
   (stereoCalibrate), Rektifizierung, erste Tiefenmessung vs. Maßband
2. **Lokalisierungsalgorithmus** — Feature-Detektion (ORB/SIFT/AKAZE) auf
   natürlichen Objekten, 3D-Position via Stereo-Disparität, Pose relativ zu
   vermessenen Referenzpunkten
3. **Validierung** — systematische Messreihen, Fehlermetriken (mm, Grad)
   gegen Referenz
4. **Ausblick** — SLAM/visuelle Odometrie, nur konzeptionell in der Arbeit

Aktuelle Phase: **1** (Dev-Workflow-Setup: SSH/VS Code/Claude Code auf dem
Pi, danach Hardware-Montage + Bring-up)

## Repo-Struktur

```
et-projekt/
  CLAUDE.md
  requirements.txt
  src/
    calibration/   # intrinsic/extrinsic Kalibrierung, Rektifizierung
    capture/        # Kamera-I/O, synchronisierte Bildaufnahme
    localization/   # Feature-Detektion, Disparität, Pose-Schätzung
    evaluation/      # Messreihen, Fehlermetriken
  tests/            # pytest, reine Logik ohne laufende Kamera testbar
  scripts/          # visuelle Sanity-Check-Skripte (siehe unten)
  data/
    calibration_images/
    reference_points.yaml   # vermessene Referenzpunkte im Testraum
  results/
    calibration/    # Kalibrierergebnisse, versioniert mit Datum
    measurements/   # Messreihen-Ergebnisse
  docs/
    decisions.md    # Entscheidungs-Log (siehe unten)
```

Reine Logik (Berechnung) von I/O (Kamerazugriff, Dateisystem) trennen —
Kernfunktionen sollen ohne laufende Kamera testbar sein.

## Nachvollziehbarkeit / Test- & Validierungsstruktur

Ziel: Code und Code-Änderungen müssen jederzeit nachvollziehbar bleiben,
auch bei KI-generiertem Code ("Vibe Coding"-Risiko: Überblick verlieren).

- **Git-Disziplin**: kleine, atomare Commits pro logischem Schritt.
  Commit-Messages nennen das *Warum*, nicht nur das *Was*. Kein Commit ohne
  vorher `git diff` gelesen zu haben.
- **Unit-Tests (pytest)**: jede neue Funktion in `src/` bekommt mind. einen
  Test in `tests/` mit bekanntem Input/Output. Tests laufen ohne Kamera.
- **Visuelle Sanity-Check-Skripte** (`scripts/`, getrennt von Unit-Tests):
  - `check_calibration.py` — Reprojection-Error-Plot
  - `check_rectification.py` — rektifizierte Bilder mit horizontalen
    Referenzlinien (müssen sich links/rechts decken)
  - `check_disparity.py` — Disparitätskarte visualisieren
  - Zweck: CV-Fehler sind oft nur visuell erkennbar, nicht nur an Zahlen
- **Ergebnis-Log** (`results/`): jede Kalibrierung/Messreihe als eigene
  Datei mit Datum + Parametern + Kennzahlen, nicht überschreiben
- **Entscheidungs-Log** (`docs/decisions.md`): kurze Einträge bei
  nicht-trivialen Entscheidungen ("Warum ORB statt SIFT", "Warum dieser
  Schwellwert") — auch als Grundlage für die schriftliche Arbeit

## Regeln für Claude Code (Arbeitsweise in diesem Repo)

- Vor jeder nicht-trivialen Änderung kurz erklären, was und warum geändert
  wird
- Nie ungefragt committen — der User liest den Diff und entscheidet
- Zu neuer Logik in `src/` immer einen Test in `tests/` mitliefern
- Bei Unsicherheit über Ansatz/Threshold: Rückfrage statt Annahme, und
  Begründung ggf. in `docs/decisions.md` festhalten

## Architektur-Vorgabe

Siehe Repo-Struktur oben. Logik und I/O getrennt halten.

## Konventionen

- Sprache Code/Kommentare: Englisch (Standard-Konvention)
- Doku/Commit-Messages: Deutsch oder Englisch, konsistent halten
- Python + OpenCV, venv für Dependencies
- Kalibrier-Pattern: klassisches Schachbrett (nicht ChArUco, basiert auf ArUco)

## Repo

https://github.com/Ombutztante/et-projekt (privat)
