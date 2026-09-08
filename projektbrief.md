# Projektbrief — Stereo-Vision-Lokalisierung (Rover, ERC-Vorbereitung)

Stand: 2026-08-31

## Titel
Entwicklung und Evaluation eines Vision-Moduls zur markerbasierten
Selbstlokalisierung eines Kamerasystems — **Update: markerbasiert → merkmalbasiert
(natürliche Features statt ArUco)**. **Update 2026-09-04: map-based →
einfache Visuelle Odometrie (VO) ohne Loop-Closure**, siehe Methode/Roadmap
unten.

- Betreuer: Prof. Steffen Borchers-Tigasson, SoSe 2026
- Kontext: Grundlage für spätere Rover-Navigation, European Rover Challenge
- Deadline: wenige Wochen, aber Vollzeit verfügbar (Semesterferien)
- Deliverable: nur schriftliche Arbeit + Code, keine Präsentation/Demo
- Scope: prototypische Umsetzung / Proof-of-Concept

## Ziel
Stereo-Kamerasystem bestimmt Position + Orientierung in einem definierten
Testbereich (Innenraum ~10×10m, Nahbereich 0,3–2m) anhand natürlicher Objekte/
Landmarken im Raum — **kein ArUco**, weder als primäre Methode noch als
Cross-Validation. Ergebnis als wiederverwendbares Modul, das sich später leicht
in eine ROS2-Architektur einbinden lässt — ROS2-Integration selbst ist NICHT
Teil dieses Projekts, nur die Code-Struktur soll das leicht ermöglichen.

## Hardware (fix, bestellt/vorhanden)
- Raspberry Pi 4B — primäre Entwicklungsplattform. Kamera (B0266) noch nicht
  physisch montiert/getestet.
- Jetson Nano — vom Professor gestellt, Modell noch unbekannt, spätere Portierung
- Arducam B0266 Stereo-Kit: 2× OV9281 Global-Shutter, Camarray-HAT, CSI,
  hardware-synchronisiert

## Testumgebung
- Innenraum ca. 10×10m, Kamera fix während Messung
- Nahbereich 0,3–2m
- Ground Truth: Maßband (PoC-Niveau ausreichend)

## Methode
Primär: Stereo-Vision, Tiefe über Disparität (StereoSGBM/Block-Matching, OpenCV).
Feature-Detektion (ORB/SIFT/AKAZE) auf natürlichen Objekten im Testraum.

**Update 2026-09-04**: statt map-based (PnP gegen vorvermessene Referenz-
punkte) jetzt einfache Visuelle Odometrie (VO) ohne Loop-Closure —
Kamerabewegung wird durch zeitliches Feature-Matching zwischen aufeinander-
folgenden Aufnahmen + Stereo-Triangulation geschätzt und zu einer
Trajektorie aufsummiert, verankert an einem einmalig vermessenen
Startpunkt. Grund: realistischer für ein Rover-Szenario ohne vorherige
Umgebungsvermessung (ERC-Analogie: ein echter Rover kann den Zielbereich
nicht vorher von Hand vermessen), nutzt dieselben Kernbausteine wie der
ursprüngliche Plan (ORB, Stereo-Triangulation), spart die Mehrpunkt-
Vermessung. Akzeptierte Einschränkung: unkorrigierte Drift über die
Strecke (kein Loop-Closure, keine globale Optimierung) — wird in der
Arbeit mit ATE/RPE-Metriken gemessen und offen diskutiert statt behoben.
Details/Alternativenabwägung: `docs/decisions.md`.

Kalibrier-Pattern: klassisches Schachbrett (nicht ChArUco).

## Roadmap
1. Stereo-Kalibrierung (intrinsisch, extrinsisch, Rektifizierung, erste
   Tiefenvalidierung)
2. Feature-basierte Visuelle Odometrie (natürliche Features, 3D-Position,
   zeitliches Matching zwischen Aufnahmen, Pose-Verkettung zu einer
   Trajektorie, verankert an einem Startpunkt)
3. Systematische Messreihen, Trajektorien-Fehler (ATE/RPE) gegen
   Maßband-Ground-Truth-Wegpunkte
4. Ausblick: volles SLAM (Loop-Closure, Bundle Adjustment) als Erweiterung
   der implementierten VO — nur konzeptionell, nicht implementiert

## Projekt-Bereiche (Work Breakdown)
A. Projektorganisation & Infrastruktur (GitHub, Overleaf, Doku-Log)
B. Hardware-Aufbau & Testumgebung (Montage, Referenzpunkte vermessen)
C. Software-/Dev-Setup (Bring-up, venv, Code-Architektur)
D. Kalibrierung (Stufe 1)
E. Lokalisierungsalgorithmus (Stufe 2)
F. Validierung & Messreihen (Stufe 3)
G. Wissenschaftliche Dokumentation (durchgehend parallel)
H. Ausblick/Bonus (Stufe 4, nur wenn Zeit reicht)

Reihenfolge: A+C(Setup) sofort, B(Testraum) parallel dazu, dann D→E→F
strikt sequenziell, G durchgehend, H optional am Ende.

## Software-Stack
- Python + OpenCV, venv
- Modularer Code (calibration/, capture/, localization/, evaluation/),
  ROS2-integrationsfreundlich, aber kein ROS2 jetzt
- Code/Kommentare Englisch, Doku Deutsch/Englisch konsistent

## Workflow / Setup
- Implementierung lokal in VS Code + Claude Code (diese Session hat keinen
  Zugriff auf den Pi) — diese Session ist für Planung/Konzepte/Review,
  **kein** vollständiger Code mehr hier
- `CLAUDE.md` im Repo-Root als Kontext für lokale Claude-Code-Sessions
  (Inhalt an User übergeben, 2026-08-31)

## Repo & Doku
- GitHub: https://github.com/Ombutztante/et-projekt (privat), main gepusht
- Overleaf: ET-Projekt aufgesetzt

## Aktueller Stand (2026-08-31)
- Phase 0 (Infrastruktur) abgeschlossen: GitHub-Repo live, Overleaf
  aufgesetzt, CLAUDE.md erstellt
- Phase 1 (Hardware-/Dev-Setup) als Nächstes: B0266 physisch montieren,
  Kamera-Bring-up-Test (libcamera, Stereo-Sync-Test), venv + Code-Grundgerüst
