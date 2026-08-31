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

- Raspberry Pi 4B — primäre Entwicklungsplattform
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

Aktuelle Phase: **0 → 1** (Repo/Doku-Setup abgeschlossen, als Nächstes
Hardware-Bring-up: B0266 physisch montieren, Kamera-Treiber testen)

## Architektur-Vorgabe

Code modular und klar getrennt halten, damit später ein ROS2-Wrapper dünn
bleiben kann. Grobe Modulaufteilung:

- `calibration/` — Intrinsic/Extrinsic-Kalibrierung, Rektifizierung
- `capture/` — Kamera-I/O, synchronisierte Bildaufnahme
- `localization/` — Feature-Detektion, Disparität, Pose-Schätzung relativ
  zur Map
- `evaluation/` — Messreihen, Fehlermetriken, Auswertung

Reine Logik (Berechnung) von I/O (Kamerazugriff, Dateisystem) trennen —
Kernfunktionen sollen ohne laufende Kamera testbar sein.

## Konventionen

- Sprache Code/Kommentare: Englisch (Standard-Konvention)
- Doku/Commit-Messages: Deutsch oder Englisch, konsistent halten
- Python + OpenCV, venv für Dependencies
- Kalibrier-Pattern: klassisches Schachbrett (nicht ChArUco, basiert auf ArUco)

## Repo

https://github.com/Ombutztante/et-projekt (privat)
