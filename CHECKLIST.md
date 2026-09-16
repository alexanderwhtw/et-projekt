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
- 🟢 Capture-Konzept (`src/capture`) muss Aufnahme-Sequenzen an mehreren, sich bewegenden Kamerapositionen unterstützen (Stop-and-Shoot), nicht mehr nur eine fixe Einzelaufnahme wie bisher getestet — erledigt in Tag 5, siehe unten (`session.capture_indexed_pair()` + `sequence.next_free_index()`, resumable/indexed, generisch für Kalibrierung und VO-Sequenzen)

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
- 🟢 ~~Keine echten Kalibrieraufnahmen vorhanden~~ (`data/calibration_images/` weiterhin leer) — die gesamte Pipeline ist bisher nur an synthetischen Daten mit bekannter Ground Truth verifiziert, noch nicht an einem einzigen echten Kamerabild. Nächster harter Blocker für "erste Tiefenmessung vs. Maßband" (Phase 1 laut CLAUDE.md-Roadmap). — behoben noch am selben Tag, siehe "Update (später am Tag 5)" unten
- 🟢 ~~`src/capture/` (Kamera-I/O, Stop-and-Shoot-Sequenzaufnahme) noch nicht implementiert~~ — ohne das keine echten VO-Sequenzen möglich, weiterhin offen aus dem Methodenwechsel-Eintrag oben. — behoben noch am selben Tag, siehe "Update (später am Tag 5)" unten
- 🟡 `data/reference_points.yaml` weiterhin leer (`points: {}`) — der Pflicht-Startpunkt fehlt, wird für `trajectory.py`s Startpose-Verankerung gebraucht, sobald echte Daten verarbeitet werden.
- 🟡 RANSAC-Parameter (`inlier_threshold` = 2cm, `max_iterations` = 200) sind begründete Startwerte, noch nicht gegen echtes Kamera-/Messrauschen validiert — bei der ersten echten Datenaufnahme prüfen und ggf. in `docs/decisions.md` nachtragen.
- 🟡 `check_disparity.py` (dichte Disparitätskarte) ist der letzte offene Sanity-Check-Stub aus `CLAUDE.md` — nicht blockierend (die VO-Pipeline nutzt sparse Features, keine dichte Disparität), aber als zusätzliche Anschauungsgrafik für den Bericht noch offen.
- 🟢 ~~Kein Kalibrier-Orchestrator analog zu `vo_pipeline.py`~~ (der Manifest laden → Ecken erkennen → Intrinsics/Extrinsics/Rektifizierung → Ergebnis speichern in einem Aufruf verkettet) — bisher nur die Einzelbausteine, bewusst so belassen, bis echte Kalibrierbilder vorliegen. — behoben noch am selben Tag (`scripts/run_calibration.py`), siehe "Update (später am Tag 5)" unten

### Update (später am Tag 5): erste echte Kalibrierung + Tiefenmessung

- 🟢 `src/capture/` implementiert (`camera`, `sequence`, `session`, 10 Tests) — behebt den oben offenen Punkt.
- 🟢 Kalibrier-Orchestrator (`scripts/run_calibration.py`) implementiert — behebt den oben offenen Punkt.
- 🟢 **Erste echte Kalibrieraufnahmen**: 20 Bildpaare (19 nutzbar), Distanz 0,5–2m, mit horizontaler/vertikaler Kippung und Positionsvariation. Behebt den oben als 🔴 markierten Blocker.
- 🟢 Kalibrierung auf echten Daten gerechnet: Intrinsics-Reprojection-Error 0,29px, Baseline 61,36mm vs. 60mm Maßband-Referenz (~2,3% Abweichung) — Pipeline funktioniert nachweislich auch auf echten Bildern, nicht nur synthetisch.
- 🟡 **Tiefenmessung vs. Maßband**: 6,2–7,5% Abweichung bei zwei getesteten Distanzen (0,7m, 1,39m). Ursache nicht abschließend geklärt (Baseline- und Tiefenfehler weichen in unterschiedliche Richtungen ab, passt nicht zu einem einfachen Skalierungsfehler); wahrscheinlichster Kandidat ist die bekannte Wölbung des nur aufgeklebten Schachbretts. Für den aktuellen Prototyp-Stand akzeptiert, Ursachenklärung bewusst auf die Fine-Tuning-Phase gegen Projektende verschoben — kein Blocker für Phase 2. Details in `docs/decisions.md` (2026-09-07).
- 🟡 Fund unterwegs: `find_checkerboard_corners()` lieferte auf dem Pi (OpenCV 4.10.0) ein anderes Array-Format als auf dem Mac-Dev-System (OpenCV 5.0.0) — gefixt, siehe `docs/decisions.md`. Lehre: Hardware-nahe Module müssen auf der Zielplattform mitgetestet werden.
- 🟡 RANSAC-Parameter (`inlier_threshold`, `max_iterations`) weiterhin nicht gegen echte Daten validiert — dafür wird jetzt eine echte VO-Bildsequenz gebraucht (noch keine aufgenommen, nur Kalibrierbilder bisher).
- 🟡 `data/reference_points.yaml` weiterhin leer — weiterhin offen.

## Tag 6 (2026-09-08, geplant) — erste echte VO-Sequenz End-to-End

Ziel: die bisher nur an synthetischen Daten geprüfte `vo_pipeline` einmal
komplett an echten, bewegten Kameraaufnahmen durchspielen — größte
verbleibende Lücke, da Kalibrierung (Phase 1) und VO-Algorithmus (Phase 2)
bisher nur getrennt validiert wurden (siehe Tag 5).

- 🟢 Startpunkt im Testraum vermessen (Maßband) und in
  `data/reference_points.yaml` eintragen (Pflicht-Ursprung für
  `trajectory.py`s Startpose-Verankerung) — Ursprung + 6 Wegpunkte
  (20cm-Schritte) eingetragen
- 🟢 Kurze Testroute festgelegt: reine Lateralbewegung entlang eines
  ~1,2m-Tisches, 20cm-Schritte, Kamera-Ausrichtung sollte konstant bleiben
- 🟢 Aufnahme-Skript `scripts/capture_vo_frame.py` angelegt (nicht-
  interaktive Einzelaufnahme, analog zu `capture_one_calibration_image.py`,
  ohne Board-Erkennung)
- 🟢 Echte VO-Bildsequenz aufgenommen: 7 Bildpaare, 0–120cm,
  `data/vo_sequences/2026-09-08_tisch_translation/`
- 🟢 `vo_pipeline` auf der echten Sequenz gelaufen (neues
  `scripts/run_vo_sequence.py`) — erste echte End-to-End-Trajektorie
  berechnet, siehe `docs/decisions.md` (2026-09-08)
- 🟢 Ergebnis-Trajektorie gegen Maßband-Ground-Truth gegengecheckt: Frames
  0–5 (0–100cm) mit moderatem, erwartetem Drift (5,5–23,2cm Fehler),
  Frame 6 (120cm) ein erklärter Ausreißer (Merkmalsschwund in der Ferne,
  4 RANSAC-Inlier) — Details in `docs/decisions.md`
- 🟡 RANSAC-Parameter (`inlier_threshold`, `max_iterations`) unverändert
  gelassen — der heutige Ausreißer war ein Merkmalsknappheits-, kein
  Schwellwert-Problem. Validierung an einer Sequenz mit durchgehend
  ausreichender Merkmalsdichte weiterhin offen.
- 🟢 Ergebnisse in `results/measurements/2026-09-08_vo_sequence_test/`
  abgelegt (`trajectory.yaml`)

### Ausblick: mobiler Wagen mit periodischer Live-VO (finaler Validierungsaufbau)

- 🟡 Idee (User, 2026-09-08): Kamera auf rollende, ggf. 3D-gedruckte
  Halterung montieren, frei durch den Raum fahren, dabei im 1-2s-Takt
  automatisch aufnehmen + live auswerten statt nachträglichem Batch-Lauf.
  Details/Einschätzung in `docs/decisions.md` (2026-09-08). Nicht jetzt
  umsetzen — erst die heutigen Framing-/Ausrichtungs-Schwachstellen in
  einer saubereren Stop-and-Shoot-Sequenz adressieren, dann Aufnahme- und
  Verarbeitungs-Latenz einzeln benchmarken, bevor in Mobilität/Live-Betrieb
  investiert wird.

## Tag 7 (zurückgestellt) — zweite VO-Sequenz (sauberes Framing + Rotation), freihändig

🔴 **Zurückgestellt (2026-09-10)**: User bewertet eine Wiederholungsmessung
jetzt als unnötig — der Tag-6-Test war grundsätzlich funktional, der
Ausreißer ist bereits ursachenerklärt. Priorität: erst einen vollständig
funktionalen Gesamtstand erreichen, Wiederholungs-/Optimierungsmessungen
erst mit sauberem Aufbau + besserem Testraum. Siehe `docs/decisions.md`
(2026-09-10). Punkte unten bleiben als Rückstand stehen, nicht verworfen.

Kein fester Tisch-Aufbau verfügbar — Aufnahme freihändig, Ground-Truth
über Bodenmarkierungen (Klebeband/Kreide) + Maßband statt Tischkante.

- 🟡 Route mit Bodenmarkierungen festlegen und abmessen (Punkte alle
  ~20-30cm), an jedem Punkt auf texturreiche Objekte (Schrank/Vorhang o.ä.)
  achten — bewusst gegen den heute gefundenen Merkmalsschwund in der Ferne
  gegensteuern (siehe `docs/decisions.md`, 2026-09-08)
- 🟡 Zweite Translations-Sequenz aufnehmen (wiederholt den heutigen Test,
  diesmal mit stabilerer Kamera-Ausrichtung) — prüfen, ob der Ausreißer bei
  fortschreitender Distanz dadurch verschwindet oder abgeschwächt wird
- 🟡 Zusätzliche Sequenz mit Rotation (nicht nur reine Translation wie
  heute) aufnehmen — nächster Schwierigkeitsgrad, prüft ob Kabsch/RANSAC
  auch Rotationsanteile korrekt schätzt
- 🟢 Design-Frage geklärt (2026-09-15, vor der heutigen zweiten Sequenz):
  Ground-Truth liegt jetzt pro Sequenz direkt neben den Bildern
  (`data/vo_sequences/<name>/ground_truth.yaml`), `reference_points.yaml`
  nur noch für die Achsenkonventions-Doku. Tag-6-Punkte umgezogen,
  `run_vo_sequence.py`/`plot_trajectory_map.py` angepasst, Tests weiterhin
  grün. Details in `docs/decisions.md` (2026-09-15).
- 🟢 ~~(Bonus, falls Zeit) `scripts/plot_trajectory_map.py`~~ — vorgezogen
  auf Tag 8 (2026-09-10), siehe dort
- 🟡 Beide neuen Sequenzen mit `run_vo_sequence.py` auswerten, Ergebnisse
  in `results/measurements/` ablegen und in `docs/decisions.md`
  dokumentieren
  investiert wird.

## Tag 8 (2026-09-10) — Top-Down-Trajektorienkarte, Entscheidung: Tag 7 zurückgestellt

- 🔴 Entscheidung (User): Wiederholungsmessung (Tag 7) jetzt zurückgestellt
  zugunsten eines vollständig funktionalen Gesamtstands; Optimierung erst
  mit sauberem Aufbau/besserem Testraum. Details in `docs/decisions.md`
  (2026-09-10).
- 🟢 `scripts/plot_trajectory_map.py` implementiert: lädt eine
  `trajectory.yaml` (aus `run_vo_sequence.py`) und optional
  `data/reference_points.yaml`, zeichnet den Top-Down-Pfad (X-Z-Ebene)
  gegen die Ground-Truth-Wegpunkte. `--exclude-frames` blendet bereits
  diagnostizierte Ausreißer aus Linie/Achsenskalierung aus, markiert sie
  aber separat (grau), statt sie stillschweigend zu entfernen.
- 🟢 Karte für die Tag-6-Sequenz erzeugt:
  `results/measurements/2026-09-08_vo_sequence_test/trajectory_map.png`
  (Frame 6 / 120cm als dokumentierter Ausreißer ausgeschlossen) — zeigt
  den erwarteten moderaten Drift der Frames 0–5 gegen die Maßband-Referenz.
- 🔴 Scope-Entscheidung (User, direkt im Anschluss): Live-VO wird doch
  konkret umgesetzt (bisher nur als Ausblick dokumentiert, siehe Tag 6),
  inkl. Rotationstest — geplant für morgen, siehe Tag 9. ROS bleibt bei
  reiner struktureller Vorbereitung (kein Code jetzt), unverändert zu
  `CLAUDE.md`. Details/Begründung in `docs/decisions.md` (2026-09-10,
  Update).

## Tag 9 (geplant, 2026-09-11) — Umbau auf Live-VO, inkl. Rotationstest

Ersetzt den zurückgestellten Tag-7-Plan (zweite statische Sequenz) fürs
Rotations-Thema — wird jetzt direkt im Live-Aufbau mitgeprüft statt in
einer separaten Stop-and-Shoot-Sequenz. Übergreifendes Ziel laut User:
Live-Messung fertig, bevor am Wochenende (ca. 2026-09-13) der reale
Aufbau (3D-Druck, plane Ausrichtung) folgt.

- 🟡 `run_vo_sequence.py`/`vo_pipeline.py` auf "aufnehmen → sofort
  verarbeiten → Zwischenstand ausgeben" umstellen (Kernbausteine der
  VO-Kette bleiben unverändert, siehe Ausblick-Einschätzung 2026-09-08)
- 🟡 Aufnahme-Latenz (`rpicam-still`) separat benchmarken, bevor ein
  Takt (1-2s) festgelegt wird — bisher nur grobe Indikation (3,9s für
  7-Frame-Batch inkl. Overhead), siehe `docs/decisions.md` (2026-09-08)
- 🟡 Bewegungsunschärfe-Frage klären: weicht von der bisherigen
  Stop-and-Shoot-Begründung in `CLAUDE.md` ab (Kamera bewegt sich
  zwischen Aufnahmen, steht aber *während* jeder Aufnahme still) — prüfen
  wie sich das beim tatsächlichen Live-Umbau verhält (siehe offener Punkt
  in `docs/decisions.md`, 2026-09-10)
- 🟡 Testroute mit Rotation (nicht nur reine Translation wie Tag 6)
  aufnehmen/auswerten — prüft ob Kabsch/RANSAC Rotationsanteile korrekt
  schätzt
- 🟡 Ergebnis mit `plot_trajectory_map.py` visualisieren und in
  `results/measurements/` + `docs/decisions.md` dokumentieren

## Tag 10 (2026-09-14) — Neuer Kamera-Aufbau (feste Montage auf Metallschiene), Neukalibrierung geplant

Mechanik-Umbau vom Wochenende (siehe Ausblick in `docs/decisions.md`,
2026-09-10-Update) umgesetzt, an Stelle des ursprünglich für den
11.09. geplanten Live-VO-Umbaus (Tag 9 oben bleibt offen, nicht verworfen).

- 🟢 Kameras neu montiert: beide OV9281-Module fest auf einer gemeinsamen
  Metallschiene verschraubt (vorher nur genagelt), Schiene auf Holzständer
  mit X-Verstrebung — mechanisch deutlich stabiler als der alte Aufbau.
  Foto `Aufbau2.HEIC` (lokal beim User, nicht im Git).
- 🟡 Rechtes Kameramodul sitzt sichtbar leicht schräg (Roll) zur
  Schienenkante — bewusst nicht mechanisch korrigiert, siehe
  `docs/decisions.md` (2026-09-14)
- 🟢 Pi-Repo aktualisiert (`git pull`), war 5 Commits hinter dem Mac
- 🟢 Baseline auf der neuen Schiene mit Maßband neu nachgemessen:
  **60mm** (auf mm genau, unverändert zum alten Referenzwert)
- 🟢 Alte Kalibrierbilder (Tag 5, altes Mount) nach
  `data/calibration_images_2026-09-07_old_mount/` archiviert, damit die
  neue Aufnahme-Session nicht versehentlich mit dem alten Datensatz
  vermischt wird
- 🟢 Neue Kalibrieraufnahmen: 12 Bildpaare (nah/weit/links/rechts/
  geschrägt/oben im Bild), unten im Bild nicht möglich (Board-Montage
  müsste dafür vom Stuhl abgenommen werden). Zwischen-Check nach 7
  Bildern zeigte noch 1,905px Extrinsics-Error — nach den restlichen 5
  Posen auf 0,955px verbessert (alter Datensatz: 0,707px bei 19 Bildern),
  Intrinsics durchgehend gut (0,22px, vgl. 0,29px alt). Ergebnis:
  `results/calibration/2026-09-14_calibration.yaml`. Berechnete Baseline
  62,57mm vs. 60mm Maßband-Referenz (+4,3%, etwas mehr als die +2,3%
  beim alten Mount)
- 🟢 Tiefenmessung vs. Maßband bei drei Distanzen (0,8m/1,3m/1,6m,
  `scripts/measure_depth.py`): **-10,4% / -10,6% / -11,1%** — auffällig
  konstanter relativer Fehler über eine Distanz-Verdopplung, deutlich
  größer als beim alten Mount (-6,2%/-7,5%) und straffer/konsistenter als
  dort. Vorzeichen widerspricht weiterhin der Baseline-Abweichung
  (Baseline zu groß, Tiefe zu klein) — schließt einen einfachen
  Quadratgrößen-Skalierungsfehler aus. Wahrscheinlichste Ursache:
  unzureichende Posen-Abdeckung der Kalibrierbilder (fehlender unterer
  Bildbereich), nicht Board-Wölbung wie bei Tag 5 vermutet — Details in
  `docs/decisions.md` (2026-09-14)
- 🟡 Root-Cause-Klärung (mehr/besser verteilte Kalibrierbilder,
  insbesondere unterer Bildbereich, ggf. mit geändertem Board-Mount ohne
  Stuhl-Abhängigkeit) bleibt offen für die Fine-Tuning-Phase — für den
  aktuellen Stand als bekannte, dokumentierte Einschränkung akzeptiert

## Tag 11 (geplant, 2026-09-15) — zweite Translationssequenz mit neuem Mount + Umstellung auf Live-VO

Zwei Ziele für morgen (User, 2026-09-14):

- 🟢 Zweite Translations-Testsequenz aufgenommen, 20cm-Schritte (analog
  Tag 6, `data/vo_sequences/2026-09-15_tisch_translation/`), neuer Mount
  + verbesserte Tisch-Markierungen + zusätzliches Objekt gegen den
  Tag-6-Merkmalsschwund. Ausgewertet mit `run_vo_sequence.py` +
  `plot_trajectory_map.py`, gegen Tag-6-Trajektorie verglichen: **gemischtes
  Ergebnis** — der Tag-6-Ausreißer bei 120cm ist behoben (keine
  Merkmalsknappheit mehr), aber der Drift pro Schritt ist durchgehend
  ~doppelt so groß wie bei Tag 6 (systematisches Untertreiben der
  Translation um ~25-35%, evtl. teilweise durch den weiterhin
  bestehenden ~7-8%-Tiefenfehler erklärt, aber nicht vollständig).
  Details in `docs/decisions.md` (2026-09-15, Update 3)
- 🟡 Umstellung von Einzelbild-Aufnahme (`capture_one_calibration_image.py`-
  artiger Stop-and-Shoot-Workflow, ein Kommando pro Frame) auf Live-VO
  (kontinuierliche Aufnahme + sofortige Verarbeitung mit laufender
  Trajektorien-Ausgabe) — entspricht dem bereits geplanten, aber noch
  nicht umgesetzten Tag 9 (siehe oben). Aufnahme-Latenz vorher kurz
  benchmarken, bevor ein Takt (1-2s) festgelegt wird (siehe
  `docs/decisions.md`, 2026-09-08)

### Zwischenschritt (ungeplant, aber vorgezogen): Fehlerbetrachtung Tiefenfehler + Neukalibrierung mit mehr Posen

Vor den beiden obigen Zielen ergab sich aus einer Diskussion über den
konstanten ~10,5%-Tiefenfehler (Tag 10) eine mathematische
Fehlerbetrachtung, die direkt zu einer konkreten Verbesserung geführt hat
— siehe `docs/decisions.md` (2026-09-15, zwei Updates) für die volle
Herleitung.

- 🟢 Fehler mathematisch in Offset- und Skalierungsanteil zerlegt
  (lineare Ausgleichsrechnung `Fehler(D) = a + k·D` mit den 3
  Tag-10-Messpunkten): ~90% Skalierungsfehler (−11,6%), nur ~1cm
  Offset-Anteil — widerlegt die Hypothese, der vom User vermutete
  Referenzpunkt-Versatz (Zollstock an Kamera-Spitze statt optischem
  Zentrum, geschätzt 5-7cm) sei der Haupttreiber
- 🟢 Neukalibrierung mit deutlich mehr Bildern (28 statt 12 nutzbar,
  freihändig gehaltenes Schachbrett statt Stuhllehnen-Mount, erstmals
  Nahbereich + unterer Bildbereich abgedeckt) — `results/calibration/2026-09-15_calibration.yaml`
- 🟡 Aufnahme-Workflow-Lernpunkt: automatischer Burst-Ansatz
  (`scripts/capture_calibration_burst.py`, alle 10s auslösen) technisch
  nicht mit Chat-Live-Feedback kombinierbar (Python-Puffer bei
  Ausgabe-Umleitung in Datei) — auf manuellen "go"-getriggerten Ablauf
  umgestellt (`capture_one_calibration_image.py`, sofortiges Feedback
  pro Bild)
- 🟢 Ergebnis: Baseline-Abweichung fast behoben (+4,3% → −0,5%),
  Tiefenfehler nur teilweise verbessert (−10,4/−10,6/−11,1% →
  **−7,0/−7,6/−8,1%** bei 0,8/1,3/1,6m) — zeigt, dass gute
  Baseline-Schätzung allein nicht für genaue Tiefe ausreicht
- 🟡 Verbleibender ~7-8%-Tiefenfehler als bekannte Einschränkung für die
  Fine-Tuning-Phase akzeptiert, keine weitere Kalibrier-Iteration jetzt
  (User-Entscheidung, passt zum Projektprinzip "erst funktionale
  Pipeline, dann Fine-Tuning")


## Tag 12 (geplant, 2026-09-17) — Rotationstest mit echten Daten + Umstellung auf Live-VO

🔴 **Verschoben von 2026-09-16 auf 2026-09-17**: kein Pi-Zugriff am
2026-09-16, beide Punkte unten brauchen die Kamera. Stattdessen an diesem
Tag `src/evaluation/` (ATE/RPE) implementiert, siehe Zwischenschritt
unten.

Reihenfolge bewusst so gewählt (Diskussion 2026-09-15, siehe
`docs/decisions.md`): Rotation zuerst, weil dafür kein neuer Code nötig
ist (Kabsch-Pose-Schätzung unterstützt volle Rotation+Translation bereits,
auf synthetischen Daten mit <0,1° Fehler verifiziert, siehe
`tests/test_pose_estimation.py::test_estimate_relative_pose_recovers_known_rotation_and_translation`)
— nur nie an echten Kameradaten getestet, weil beide bisherigen echten
Sequenzen (Tag 6, Tag 11) bewusst reine Translation mit konstanter
Kamera-Ausrichtung waren. Live-VO danach, weil es am bewiesenermaßen
funktionierenden Kern aufbauen soll, nicht an einer noch ungetesteten
Annahme.

- 🟡 Kurze Sequenz mit bekannter, gemessener Rotation aufnehmen (Kamera an
  einer Position um einen gemessenen Winkel drehen, plus ggf. Translation),
  mit `run_vo_sequence.py` auswerten — prüft, ob die Pose-Schätzung auch
  mit Rotationsanteil auf echten Bildern plausibel bleibt
- 🟡 Umstellung von Einzelbild-Aufnahme auf Live-VO (kontinuierliche
  Aufnahme + sofortige Verarbeitung mit laufender Trajektorien-Ausgabe) —
  entspricht dem seit Tag 9 geplanten, bisher nicht umgesetzten Schritt.
  Aufnahme-Latenz vorher kurz benchmarken, bevor ein Takt (1-2s)
  festgelegt wird (siehe `docs/decisions.md`, 2026-09-08)
- 🟡 Danach Status-Check: Phase 2 (VO-Algorithmus) wäre damit funktional
  abgeschlossen, Phase 3 (systematische Messreihen, ATE/RPE-Metriken)
  bleibt aber weiterhin größtenteils offen — Projekt ist NICHT "fertig bis
  auf Optimierung", siehe Diskussion `docs/decisions.md` (2026-09-15)

### Zwischenschritt (2026-09-16, kein Pi-Zugriff): `src/evaluation/` (ATE/RPE) implementiert

Rotationstest + Live-VO-Latenz-Benchmark brauchen beide die Kamera, daher
auf morgen verschoben (Details siehe unten). Stattdessen den größten
nicht-Hardware-Blocker für Phase 3 angegangen.

- 🟢 `src/evaluation/metrics.py`: `absolute_trajectory_error()` (ATE),
  `relative_pose_error()` (RPE, Translation), `rotation_error_deg()`
  (Baustein für den Rotationstest) — 11 neue Tests, 71/71 Tests grün.
  Design-Entscheidung (kein Trajektorien-Alignment vor der
  Fehlerberechnung, bewusst anders als TUM-RGBD-Standard) begründet in
  `docs/decisions.md` (2026-09-16).
- 🟢 `scripts/evaluate_trajectory.py` gegen beide echten Sequenzen (Tag 6,
  Tag 11) gelaufen — erste belastbare ATE/RPE-Zahlen statt nur Prosa-
  Beschreibung, bestätigen quantitativ den bekannten Ausreißer (Tag 6) und
  den systematischen Pro-Schritt-Drift (Tag 11). Reports:
  `results/measurements/2026-09-08_vo_sequence_test/evaluation.yaml`,
  `results/measurements/2026-09-15_vo_sequence_test/evaluation.yaml`.
- 🟡 `rotation_error_deg()` noch nicht in `relative_pose_error()`
  integriert — `trajectory.yaml` speichert aktuell nur Positionen, keine
  vollen Posen. Vor dem Tag-12-Rotationstest ergänzen, siehe
  `docs/decisions.md` (2026-09-16).
- 🟢 **Live-VO-Umstellung (Code-Teil)**: `src/localization/vo_pipeline.py`
  hat jetzt `init_vo_step()`/`step_vo_pipeline()` als Kernprimitive (ein
  Frame rein, eine Pose raus) — genau das, was die Live-Aufnahmeschleife
  morgen pro Frame aufrufen wird. `run_vo_pipeline()` (Batch) ist jetzt nur
  noch eine dünne Schleife darüber. `run_vo_sequence.py` nutzt dieselbe
  Frame-für-Frame-Schleife, Pose wird direkt nach jedem Frame ausgegeben.
  4 neue Tests (u.a. Batch==Streaming-Regressionstest), 75/75 Tests grün.
  Details in `docs/decisions.md` (2026-09-16, Teil 2).
- 🔴 **Nebenbefund**: RANSAC in `run_vo_sequence.py` lief bisher ohne
  festen Seed — Fehler bei merkmalsarmen Frames (z.B. Tag-6-Frame-6)
  schwankte zwischen Läufen derselben Sequenz um Faktor 7 (26cm bis
  195cm). Gefixt: neuer `--seed`-Parameter (Default 0), Seed wird jetzt in
  `trajectory.yaml` mitgespeichert. Historische Fehlerwerte in
  `docs/decisions.md` waren dadurch nie exakt reproduzierbar — für die
  Arbeit: Größenordnung/Tendenz zählt, nicht die exakte Zentimeterzahl bei
  einzelnen merkmalsarmen Frames. Details in `docs/decisions.md`
  (2026-09-16, Teil 2).
- 🟡 Reine I/O-Verdrahtung für die eigentliche Live-Aufnahmeschleife
  (`camera.capture_frame()` statt Datei-Laden pro Schritt) noch offen —
  ungetestet ohne Kamera nicht sinnvoll zu schreiben, für morgen (Tag 12).

## Vorgemerkt (nach Phase 3) — Parameter-Sensitivitätsprüfung statt Optimierungs-Loop

Aus der Diskussion 2026-09-15 (siehe `docs/decisions.md`): Idee (User) war
ein automatisierter Optimierungs-Loop, der gegen eine einzelne bekannte
Sequenz VO-interne Parameter (RANSAC-Schwellwert, ORB-Feature-Anzahl,
Matching-Ratio, …) durchsucht. Zurückgestellt, mit Gegenvorschlag:

- 🟡 Erst Phase 3 sauber abschließen (ATE/RPE-Metriken in
  `src/evaluation/`, mehrere echte Messreihen) — eine Parameter-Prüfung
  gegen eine noch ad-hoc Fehlermetrik ist wenig aussagekräftig
- 🟡 Dann: begründete Sensitivitätsprüfung (wenige, bewusst gewählte
  Werte pro Parameter, nicht automatisiert durchsucht) statt Blackbox-
  Optimierung — passt besser zum Projektprinzip "Nachvollziehbarkeit"
  (`CLAUDE.md`)
- 🟡 Über **mindestens zwei** unabhängige Sequenzen validieren (an einer
  einstellen, an der anderen prüfen), nicht nur eine — sonst Risiko von
  Überanpassung an eine einzelne Aufnahme/Szene
- 🟡 Einordnung: der bisher dominante Fehler (Tiefen-Skalierung aus der
  Kalibrierung, ~7-8%) wird durch VO-interne Parameter (ORB/RANSAC)
  vermutlich nicht behoben, da diese nur die Punktauswahl/Robustheit
  beeinflussen, nicht die zugrunde liegenden Tiefenwerte — Erwartungen
  entsprechend dämpfen
