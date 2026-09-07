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

- 🟢 Fokus: keine manuell zugängliche Einstellmöglichkeit am Kameramodul gefunden, lässt sich nicht verschieben — Punkt als nicht-aktionabel akzeptiert (nichts zu fixieren), siehe `docs/decisions.md`
- 🟢 Schachbrett zugeschnitten (6×7 Innenecken) — per Testaufnahme verifiziert: `findChessboardCornersSB` findet 7×7 nicht mehr, 6×7 zuverlässig und konsistent in L/R, Ecken-Reihenfolge-Mehrdeutigkeit aus Tag 3 behoben
- 🟢 Schachbrett-Montage: auf Kartonplatte geklebt, an Stuhllehne befestigt, für aktuelle Funktions-Phase akzeptiert — feste Montage auf harter Unterlage bleibt offen fürs spätere Fine-Tuning, siehe `docs/decisions.md`
- 🟢 Quadratgröße mit Lineal/Messschieber nachgemessen: **24mm bestätigt** (Sollwert = Realwert)
- 🟡 Beleuchtung für Kalibrieraufnahmen gezielt prüfen (gleichmäßig, keine Reflexionen/Überbelichtung) — zurückgestellt, Prinzip ab jetzt: erst funktionale Pipeline, dann Fine-Tuning, siehe `docs/decisions.md`
- 🟡 Testaufnahme im Nahbereich (~0,3–0,4m) — verschoben, aktueller Prototyp-Aufbau lässt sich nicht ohne größeren Umbau für Nahbereich anpassen, siehe `docs/decisions.md`
- 🟢 Namenskonvention für `data/calibration_images/` festgelegt: `left_NNN.png`/`right_NNN.png` (3-stelliger Index als L/R-Paar-ID) + Begleit-Manifest `manifest.csv` für Pose-/Settings-Metadaten, siehe `docs/decisions.md`

**Prinzip ab jetzt (siehe `docs/decisions.md`):** erst eine durchgängig funktionierende Kalibrier-/Lokalisierungs-Pipeline bauen, auch mit bekannten Ungenauigkeiten in Mechanik/Beleuchtung/Fokus. Exaktheit/Fine-Tuning kommt in einer späteren Phase, wenn die Pipeline grundsätzlich steht.

## Methodenwechsel (2026-09-04) — map-based → Visuelle Odometrie ohne Loop-Closure

- 🔴 **Grundsatzentscheidung**: statt vorher vermessener Referenzpunkte (map-based) jetzt einfache Visuelle Odometrie (VO) — Kamerabewegung wird aus zeitlichem Feature-Matching + Stereo-Triangulation geschätzt und zu einer Trajektorie verkettet, verankert an einem Startpunkt. Details/Begründung in `docs/decisions.md`. **Weicht vom ursprünglichen, mit Betreuer-Kontext dokumentierten Projektbrief ab — bei Gelegenheit mit Prof. Borchers-Tigasson rückspiegeln.**
- 🟢 `CLAUDE.md`, `projektbrief.md`, `data/reference_points.yaml` entsprechend aktualisiert
- 🟡 `data/reference_points.yaml` befüllen: nur noch EIN Startpunkt-Ursprung nötig (Pflicht), optional ein paar Ground-Truth-Wegpunkte entlang der geplanten Testroute (nur für spätere Auswertung, nicht für den Algorithmus)
- 🟡 Capture-Konzept (`src/capture`) muss Aufnahme-Sequenzen an mehreren, sich bewegenden Kamerapositionen unterstützen (Stop-and-Shoot), nicht mehr nur eine fixe Einzelaufnahme wie bisher getestet

## Tag 5 (2026-09-07) — Software-Implementierung: VO-Pipeline (Phase 2) + Kalibrier-Pipeline (Phase 1)

### Was funktioniert
- 🟢 `src/localization/` komplett und verkettet: `features` (ORB) → `stereo_depth` (L/R-Matching + Triangulation) → `temporal_matching` (Frame_t-1↔t, Lowe's Ratio-Test) → `pose_estimation` (Kabsch 3D-3D-Alignment + RANSAC) → `trajectory` (Posen-Verkettung) → `vo_pipeline` (Orchestrator). 30 Tests, jeweils gegen synthetische Ground-Truth-Geometrie mit bekanntem Ergebnis exakt verifiziert.
- 🟢 `src/calibration/` komplett: `corners` (Eckenerkennung + Objektpunkte) → `intrinsics` (`calibrateCamera` + Pro-Bild-Reprojection-Error) → `extrinsics` (`stereoCalibrate`, exakte Rekonstruktion der real gemessenen 60mm-Baseline in synthetischen Tests) → `rectification` (`stereoRectify`, liefert `P1`/`P2` direkt kompatibel mit `stereo_depth.py`) → `io` (Manifest laden, Kalibrierergebnis als datierte YAML speichern/laden). 20 Tests.
- 🟢 Gesamt **50/50 Tests grün**, in zwei Commits versioniert (`acdacca`, `3301700`).
- 🟢 Für jedes Modul ein visuelles Sanity-Check-Skript (`scripts/check_*.py`, u.a. die beiden vorher leeren Stubs `check_calibration.py` und `check_rectification.py` jetzt implementiert) — je mit Beispielbild/-plot geprüft, nicht nur Zahlen.
- 🟢 End-to-End-Test bestätigt: komplette Kette von synthetischen Stereo-Bildern bis zur fertigen Trajektorie funktioniert zusammen (`scripts/check_vo_pipeline.py`) — <0,1° Rotationsfehler, mm-Bereich Translationsfehler über mehrere Frames.
- 🟢 Phase 1 und Phase 2 docken sauber aneinander: `P1`/`P2` aus `src/calibration/rectification.py` sind exakt das Format, das `src/localization/stereo_depth.triangulate_matches()` erwartet.

### Kritischer Befund, während der Session gelöst
- 🔴→🟢 Naive Kleinste-Quadrate-Pose-Schätzung (Kabsch) war anfällig für Ausreißer: beim ersten End-to-End-Test zeigten sich ~15% Fehlzuordnungen bereits beim Stereo-Matching, die sich zu ~39% Ausreißern in den finalen 3D-3D-Korrespondenzen aufsummierten (synthetische Testszene) — verzerrte die geschätzte Pose deutlich (5° statt ~0° Rotationsfehler). Mit RANSAC in `pose_estimation.py` (`estimate_relative_pose_ransac`) behoben, `vo_pipeline.py` nutzt jetzt ausschließlich die robuste Variante. Wichtig für die Arbeit: zeigt, dass Feature-Matching auch bei einfachen synthetischen Szenen nicht fehlerfrei ist — Ausreißer-Robustheit ist kein Nice-to-have, sondern nötig. Details in `docs/decisions.md` (2026-09-07).

### Noch offen
- 🔴 **Keine echten Kalibrieraufnahmen vorhanden** (`data/calibration_images/` weiterhin leer) — die gesamte Pipeline ist bisher nur an synthetischen Daten mit bekannter Ground Truth verifiziert, noch nicht an einem einzigen echten Kamerabild. Nächster harter Blocker für "erste Tiefenmessung vs. Maßband" (Phase 1 laut CLAUDE.md-Roadmap).
- 🟡 `src/capture/` (Kamera-I/O, Stop-and-Shoot-Sequenzaufnahme) noch nicht implementiert — ohne das keine echten VO-Sequenzen möglich, weiterhin offen aus dem Methodenwechsel-Eintrag oben.
- 🟡 `data/reference_points.yaml` weiterhin leer (`points: {}`) — der Pflicht-Startpunkt fehlt, wird für `trajectory.py`s Startpose-Verankerung gebraucht, sobald echte Daten verarbeitet werden.
- 🟡 RANSAC-Parameter (`inlier_threshold` = 2cm, `max_iterations` = 200) sind begründete Startwerte, noch nicht gegen echtes Kamera-/Messrauschen validiert — bei der ersten echten Datenaufnahme prüfen und ggf. in `docs/decisions.md` nachtragen.
- 🟡 `check_disparity.py` (dichte Disparitätskarte) ist der letzte offene Sanity-Check-Stub aus `CLAUDE.md` — nicht blockierend (die VO-Pipeline nutzt sparse Features, keine dichte Disparität), aber als zusätzliche Anschauungsgrafik für den Bericht noch offen.
- 🟡 Kein Kalibrier-Orchestrator analog zu `vo_pipeline.py` (der Manifest laden → Ecken erkennen → Intrinsics/Extrinsics/Rektifizierung → Ergebnis speichern in einem Aufruf verkettet) — bisher nur die Einzelbausteine, bewusst so belassen, bis echte Kalibrierbilder vorliegen.

