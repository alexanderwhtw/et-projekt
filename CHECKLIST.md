# Checklist

🟢 erledigt · 🟡 offen · 🔴 kritisch/broken/wichtig

## Tag 1 (2026-09-01)

- 🟢 SSH-Zugriff zum Pi (Alias `rasp-local` / `rasp-lan`)
- 🟢 Altes Projekt vom Pi gelöscht (drop_project, drop_project_01, Bilder, Videos)
- 🟢 Debug_frames & measure_logs (root-owned) gelöscht
- 🟢 Stereo-Kamera erkannt (arducam-pivariety, Slots MIPIRX2/3, 2560x800)
- 🟢 Stereo-Testbild aufgenommen & verifiziert (beide Kameras liefern synchrones Bild)
- 🟢 IPA-Tuning-Datei-Fix: Symlink `arducam-pivariety_mono.json` → `ov9281_mono.json` in `/usr/share/libcamera/ipa/rpi/vc4/` angelegt (verifiziert via `rpicam-still`)
- 🟢 Echtes git clone auf Pi (ersetzt Dateikopie)
- 🟢 GitHub-SSH-Zugriff vom Pi (Deploy-Key mit Schreibrechten)
- 🟢 Node.js 22 (NodeSource) auf Pi installiert
- 🟢 Claude Code auf Pi installiert (`~/.npm-global`, kein sudo nötig)
- 🟢 VS Code Remote-SSH Setup (Extension installiert, Server läuft auf Pi)
- 🟢 VS Code App auf Mac aktualisiert (1.73.0 → 1.135.0, via Homebrew Cask, alte Downloads-Kopie entfernt)
- 🟢 Repo-Grundgerüst gemäß CLAUDE.md angelegt (src/, tests/, scripts/, data/, results/, docs/), committet & gepusht

## Tag 2 (2026-09-02) — Vorbereitung Kalibrierung: Kamera-Settings & Sanity-Checks

### Kamera-Settings fixieren
- 🟢 Belichtung (Exposure) & Gain manuell fixieren statt Auto: 5 Testaufnahmen mit `rpicam-still --shutter/--gain` durchgespielt, Kandidatenwerte gefunden (`--shutter 3500 --gain 1.0`), dokumentiert in `docs/decisions.md` + `cal/opt_calib.md` (gitignored) — Feinjustage folgt mit echtem Schachbrett-Motiv
- 🟢 Weißabgleich: verifiziert (OV9281/B0266 ist Mono, `rpicam-still --list-cameras` zeigt `10-bit MONO`), AWB fix auf (1.0, 1.0) gesetzt, kein Einfluss auf L/R-Helligkeitsunterschied nachgewiesen (Iteration 4 in opt_calib.md)
- 🟡 Fokus auf Zielbereich (0,3–2m) scharfstellen und mechanisch fixieren (Fokusring sichern) — physischer Schritt an der Kamera, nicht remote testbar; Schärfe im Zentrum UND am Bildrand danach prüfen
- 🟢 Auflösung festgelegt: 2560x800 (volle Sensorauflösung, L+R bereits nebeneinander in einem Frame vom Camarray-HAT) — Framerate für Video-/Live-Modus noch offen (nur Stills getestet)
- 🟢 (Nebenbefund) L/R-Kanäle systematisch ~5,5–7,5 % unterschiedlich hell, reproduzierbar über 5 Durchläufe, Ursache vermutlich Sensor-/Objektiv-Unterschied, nicht AWB/CCM — Details & Begründung in `docs/decisions.md`

### Mechanik / Montage
- 🟢 Level-Check (Roll) quantifiziert per ORB-Feature-Matching + RANSAC (statt nur visuell): **Roll ≈ 2,25°**, konstanter vertikaler Versatz ~6,8 px am Bildzentrum, ~22 px Streuung über die Bildbreite (~2,7 % der Bildhöhe) — erwartungsgemäß spürbar, da Kamera aktuell nur mit Nägeln fixiert ist. Für den prototypischen Aufbau akzeptiert (stereoRectify korrigiert das), kein mechanischer Fix jetzt. Details in `docs/decisions.md`
- 🟢 Baseline (Abstand der beiden Linsenmittelpunkte) mit Maßband nachgemessen: **60 mm** — Referenzwert für Plausibilitätscheck späterer stereoCalibrate-Ergebnisse, siehe `docs/decisions.md`
- 🟢 Stabilität der Halterung geprüft: steht auf festem Tisch, in Ruhe — ausreichend für Prototyp
- 🟢 CSI-Kabel/HAT-Anschluss geprüft

### Synchronisation
- 🟢 Sync-Test verschärft: Stoppuhr (Hundertstelsekunden) auf Handy-Display in 50cm Abstand fotografiert, L/R zeigen identisch **02:59,34** — kein Zeitversatz messbar (Auflösung der Methode: ~10ms). Architektur-Begründung: nur **ein** Kamera-Device (`arducam-pivariety`), ein `SensorTimestamp` pro Frame — L/R können technisch keinen unabhängigen Zeitversatz haben. Details in `docs/decisions.md`

### Workflow / Sonstiges
- 🟢 Speicherplatz auf Pi geprüft (`df -h /`: 104G frei von 117G, 8% belegt)
- 🟢 `rpicam-still --list-controls` gibt es in dieser rpicam-apps-Version (v1.13.0) nicht (`unrecognised option`) — stattdessen relevante Controls aus `rpicam-still --help` extrahiert und dokumentiert (`--shutter`, `--gain`, `--awb`, `--awbgains`, `--denoise`, `--metering`, `--ev`, `--sharpness`)
- 🟢 Heutige Settings-Entscheidungen (Exposure/Gain-Werte, Baseline, Roll-Verkippung, Sync-Verifikation) in `docs/decisions.md` festgehalten

## Tag 3 (geplant) — übernommen von Tag 2, nicht mehr geschafft

- 🟡 Fokus auf Zielbereich (0,3–2m) scharfstellen und mechanisch fixieren (Fokusring sichern) — physischer Schritt an der Kamera; danach Schärfe im Zentrum UND am Bildrand prüfen
- 🟡 Schachbrett auf ebener, harter Unterlage montieren (nicht gewellt/gebogen)
- 🟡 Quadratgröße exakt nachmessen (mm) statt dem Druck zu vertrauen — Wert wird in `src/calibration` gebraucht
- 🟡 Beleuchtung für Kalibrieraufnahmen prüfen: gleichmäßig, keine Reflexionen/Überbelichtung auf dem Muster
- 🟡 Ein paar Schachbrett-Testaufnahmen in verschiedenen Winkeln/Distanzen (Abdeckung 0,3–2m + Bildränder), Namenskonvention für `data/calibration_images/` festlegen
- 🟡 Belichtungs-Kandidat aus Tag 2 (`--shutter 3500 --gain 1.0 --awbgains 1.0,1.0 --denoise off`) mit echtem Schachbrett-Motiv nachjustieren (weiße Felder dürfen nicht clippen)
- 🟡 Visuelle Verzeichnungsprüfung: gerade Linien nahe Bildrand auf Tonnen-/Kissenverzeichnung checken
- 🟡 Helligkeitsabgleich L/R visuell vergleichen (mit Schachbrett-Motiv)

