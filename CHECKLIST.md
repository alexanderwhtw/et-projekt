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

## Tag 3 (2026-09-03) — Schachbrett-Testaufnahmen & Belichtung nachjustiert

- 🟢 Belichtungs-Kandidat aus Tag 2 mit echtem Schachbrett-Motiv nachjustiert: `--shutter 3500` war bei den heutigen (dunkleren) Lichtverhältnissen zu knapp (Board lag im Schatten, "weiße" Felder nur ~mittelgrau, Ecken nicht erkennbar) → neuer Kandidat **`--shutter 10000 --gain 1.0 --awbgains 1.0,1.0 --denoise off`**, alle 49 Ecken zuverlässig erkannt (`cv2.findChessboardCornersSB`). Lichtverhältnisse sind also nicht stabil zwischen Sitzungen — Belichtung muss pro Session neu geprüft werden, nicht fest verdrahten
- 🟢 4 Testaufnahmen mit Positions-/Winkel-/Distanz-Variation: frontal 1m, Ecke oben-links gekippt (~1m), weit rechts stark gekippt (~1m), frontal ~2m — alle 49 Ecken jeweils zuverlässig erkannt. Bei 2m nur noch ~10,5px/Feld (Board sehr klein im Bild), Erkennung funktioniert trotzdem, aber Subpixel-Genauigkeit der Ecken dürfte dort geringer sein
- 🟢 Visuelle/quantitative Verzeichnungsprüfung: Zeilen der erkannten Eckpunkte auf Geraden-Abweichung geprüft, max. 0,37px selbst nah am rechten Bildrand → sehr geringe Linsenverzeichnung im getesteten Bereich. Details in `docs/decisions.md`
- 🟢 Helligkeitsabgleich L/R (mit Schachbrett-Motiv, quantitativ statt nur visuell): 1,2–2,9 % Unterschied auf der Board-Fläche über alle 3 Posen — deutlich kleiner als der ~6 % Szenen-Unterschied aus Tag 2 (dort ganzes, unterschiedlich beleuchtetes Bild verglichen), unkritisch
- 🔴 **Befund**: 8×8-Schachbrett (7×7 Innenecken, symmetrisch) hat empirisch bestätigte Ecken-Reihenfolge-Mehrdeutigkeit zwischen L/R (`cv2.findChessboardCorners` liefert die Punktliste in L und R teils in entgegengesetzter Reihenfolge). Für Sanity-Checks unproblematisch, aber für `stereoCalibrate` (braucht konsistente Punkt-Korrespondenz) blockierend. **→ neues asymmetrisches Muster nötig, siehe Tag 4.** Details in `docs/decisions.md`
- 🟢 (Technischer Nebenbefund) `cv2.CALIB_CB_FAST_CHECK` erzeugt bei großen/stark gekippten Brettern falsche Negative — für `src/calibration` `findChessboardCornersSB` ohne dieses Flag verwenden (`cal/check_corners.py` als Referenz)

## Tag 4 (geplant) — übernommen von Tag 2/3, nicht mehr geschafft

- 🟡 Fokus auf Zielbereich (0,3–2m) scharfstellen und mechanisch fixieren (Fokusring sichern) — physischer Schritt an der Kamera; danach Schärfe im Zentrum UND am Bildrand prüfen
- 🟡 Neues, asymmetrisches Schachbrett drucken (z.B. 9×6 Innenecken statt 7×7) — vermeidet die Ecken-Reihenfolge-Mehrdeutigkeit aus Tag 3, siehe `docs/decisions.md`
- 🟡 Schachbrett auf ebener, harter Unterlage montieren (nicht gewellt/gebogen) — aktuell nur an Stuhllehne gehalten/geklemmt
- 🟡 Quadratgröße exakt nachmessen (mm) statt dem Druck zu vertrauen (Sollwert 24mm, real noch nicht mit Lineal/Messschieber verifiziert) — Wert wird in `src/calibration` gebraucht
- 🟡 Beleuchtung für Kalibrieraufnahmen gezielt prüfen: gleichmäßig, keine Reflexionen/Überbelichtung auf dem Muster (bisher nur indirekt über Belichtungs-Settings behandelt)
- 🟡 Testaufnahme im Nahbereich (~0,3–0,4m) — bisher nur ~1m und ~2m getestet
- 🟡 Namenskonvention für `data/calibration_images/` festlegen (z.B. `left_NNN.png`/`right_NNN.png` oder Pose-Label im Dateinamen)

