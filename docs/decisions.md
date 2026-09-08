# Entscheidungs-Log

Kurze Einträge zu nicht-trivialen Entscheidungen im Projekt (Algorithmus-
Wahl, Schwellwerte, Architektur-Entscheidungen). Dient auch als Grundlage
für die schriftliche Arbeit.

## Format

**YYYY-MM-DD** — Kurztitel der Entscheidung

- Kontext:
- Alternativen:
- Begründung:

## 2026-09-02 — Manuelle Belichtung statt Auto-Exposure für Kalibrieraufnahmen

- Kontext: Kalibrieraufnahmen (Schachbrett, mehrere Aufnahmen über Zeit)
  brauchen konstante Belichtung; Auto-Exposure würde zwischen Frames
  driften. 5 Testaufnahmen mit `rpicam-still` (verschiedene Shutter/Gain/
  AWB-Kombinationen) ausgewertet, Details in `cal/opt_calib.md` (Ordner
  `cal/` ist gitignored — Ad-hoc-Testbilder, nicht die finale
  Kalibrier-Datenbasis).
- Alternativen: Auto-Exposure/Auto-Gain belassen; feste Werte nur pauschal
  raten ohne Messung.
- Begründung: Manuelle Werte (`--shutter --gain`) machen Aufnahmen
  reproduzierbar. Kandidatenwerte für die Testszene: `--shutter 3500
  --gain 1.0 --awbgains 1.0,1.0 --denoise off` (Startpunkt, muss mit
  echtem Schachbrett-Motiv wegen hellerer Reflexion nachjustiert werden).
  AWB fix auf (1.0, 1.0), da Sensor Mono ist (kein Farbbild, AWB
  irrelevant). Denoise aus, um Schachbrett-Ecken nicht zu glätten.
- Nebenbefund: Linker und rechter Kanal sind systematisch ~5,5–7,5 %
  unterschiedlich hell (reproduzierbar über alle 5 Durchläufe, nicht durch
  Szeneninhalt erklärbar, nicht durch AWB/CCM verursacht — vermutlich
  Sensor-/Objektiv-Unterschied). Für Phase 2 (Feature-Matching) vermutlich
  unkritisch, für dichtes Stereo-Matching ggf. Helligkeitsnormalisierung
  als Preprocessing-Schritt in `src/capture` vormerken — keine Entscheidung
  heute nötig, nur Beobachtung.

## 2026-09-02 — Baseline (Stereo-Basisbreite) gemessen: 60 mm

- Kontext: Abstand der beiden Linsenmittelpunkte (Arducam B0266 Stereo-Kit)
  mit Maßband nachgemessen.
- Wert: **60 mm**.
- Verwendungszweck: Referenzwert für Plausibilitätscheck der Translation
  (`T`) aus `cv2.stereoCalibrate` in Phase 1 — der berechnete Baseline-Wert
  sollte nahe an dieser manuell gemessenen Distanz liegen. Maßband-Messung
  ist PoC-Niveau (siehe CLAUDE.md), keine hochpräzise Referenz.

## 2026-09-02 — Roll-Verkippung (~2,25°) akzeptiert, kein mechanischer Fix im Prototyp

- Kontext: Level-Check (Testaufnahme, ORB-Feature-Matching zwischen L/R +
  RANSAC-Fit von `dy = a + b*(x - cx)`, Skript `cal/analyze_roll.py`)
  zeigt eine Roll-Verkippung zwischen den beiden Kameras: Steigung
  b ≈ 0,0393 → Roll-Winkel ≈ 2,25°, plus konstanter vertikaler Versatz
  a ≈ 6,8 px am Bildzentrum (130 von 139 Matches als RANSAC-Inlier). Über
  die volle Bildbreite ergibt sich eine vertikale Streuung von ca. 22 px
  (~2,7 % der Bildhöhe von 800 px).
- Ursache: aktueller Prototyp-Aufbau fixiert die Kamera nur mit Nägeln,
  keine präzise Halterung — Verkippung war erwartet.
- Alternativen: Mechanische Nachjustage jetzt vs. Verkippung akzeptieren
  und softwareseitig (stereoRectify) korrigieren lassen.
- Begründung: Für den prototypischen Aufbau (PoC, kein Produktionscode,
  siehe CLAUDE.md) wird die Verkippung akzeptiert — `stereoRectify`
  korrigiert das rechnerisch, kostet aber ca. 2–3 % Bildbereich am Rand.
  Kein Blocker für Phase 1. Bei einer stabileren Halterung (spätere
  Iteration/Rover-Integration) sollte der Wert erneut geprüft werden, da
  eine geringere Verkippung mehr nutzbaren Bildbereich nach der
  Rektifizierung übrig lässt.

## 2026-09-02 — Hardware-Synchronisation L/R verifiziert (Stoppuhr-Test)

- Kontext: Tag-1-Sync-Test war nur qualitativ ("beide Kameras liefern
  synchrones Bild"). Verschärfter Test: Handy mit laufender Stoppuhr
  (Hundertstelsekunden-Anzeige) im Abstand von ca. 50 cm vor der Kamera
  positioniert, ein Still (2560x800) aufgenommen, L- und R-Bildhälfte
  digit-genau verglichen.
- Ergebnis: Beide Hälften zeigen identisch **02:59,34** — kein Zeitversatz
  erkennbar. Bild: `cal/bilder/synctest_zoom_compare.png` (gitignored).
- Zusätzliche Architektur-Begründung: `rpicam-still --list-cameras` zeigt
  nur **ein** Kamera-Device (`arducam-pivariety`), nicht zwei separate
  Streams; Metadata eines Captures enthält nur **einen** `SensorTimestamp`
  fürs komplette Frame. Das Camarray-HAT liefert L+R also als einen
  gemeinsamen, hardware-synchronisierten Ausleseprozess, kein
  nachträgliches Software-Stitching zweier unabhängiger Kameras — ein
  unabhängiger Zeitversatz zwischen L/R ist architektonisch praktisch
  ausgeschlossen.
- Einschränkung: Auflösungsgrenze der Methode liegt bei ~10ms (Hundertstel-
  Digit-Wechsel der Stoppuhr-App). Ein Sub-Millisekunden-Versatz wäre damit
  nicht nachweisbar, ist aber für Phase 1/2 (Feature-Matching, Pose bei
  ruhender Kamera) irrelevant, da die Kamera während der Messung ohnehin
  fest steht (kein Rolling-Shutter-/Bewegungsproblem, siehe CLAUDE.md).

## 2026-09-03 — Belichtung ist sitzungsabhängig, nicht fest verdrahten

- Kontext: Erste Schachbrett-Testaufnahme (1m, frontal) mit dem Tag-2-
  Kandidaten `--shutter 3500 --gain 1.0` ergab ein deutlich unterbelichtetes
  Bild (weiße Felder nur ~mittelgrau, max=100 statt >200 in der
  Board-Region) — Board stand im Schatten, während die Auto-Metering-
  Referenz von Tag 2 einen helleren, fensternahen Bereich der Szene traf.
  Ecken wurden dadurch nicht erkannt.
- Ergebnis: Mit `--shutter 10000 --gain 1.0 --awbgains 1.0,1.0 --denoise off`
  (statt 3500) alle 49 Innenecken (7x7) in L und R zuverlässig erkannt.
- Begründung/Konsequenz: Lux/Lichtverhältnisse schwanken spürbar zwischen
  Sitzungen (Tageszeit, Bewölkung, Objektposition relativ zum Fenster).
  Ein einmalig ermittelter Belichtungswert taugt nicht als dauerhafte
  Konstante — vor jeder Aufnahmeserie kurz mit `cv2.findChessboardCorners`
  gegenchecken, ob die Ecken erkannt werden, statt blind einen alten Wert
  zu übernehmen. Für die spätere `src/capture`-Implementierung: entweder
  Belichtung pro Session neu kalibrieren (kurzer Auto-Messdurchlauf, dann
  fixieren) oder mit etwas mehr Sicherheitsabstand nach oben arbeiten.

## 2026-09-03 — Schachbrett muss asymmetrisch sein (7x7 verursacht Ecken-Vertauschung)

- Kontext: Beim ersten Eckenerkennungs-Test (Board 1m, frontal, 8x8 Felder
  = 7x7 Innenecken) zeigte die Visualisierung (`cv2.drawChessboardCorners`)
  in L und R einen **entgegengesetzten** Farbverlauf der Punktreihenfolge.
  Nachgerechnet: `L[0]` ≈ (703.6, 493.5) liegt an (fast) derselben
  physischen Ecke wie `R[-1]` ≈ (651.6, 501.6) — die Punktlisten sind also
  zwischen L und R komplett gegenläufig indiziert.
- Ursache: 7x7 ist ein symmetrisches Muster (gleiche Zeilen-/Spaltenzahl).
  `cv2.findChessboardCorners` legt die Scan-Startecke/-Richtung anhand
  lokaler Bildmerkmale fest, nicht anhand einer global eindeutigen
  Markierung — bei einem symmetrischen Muster kann diese Wahl zwischen zwei
  Aufnahmen (hier: L vs. R desselben Frames) unterschiedlich ausfallen,
  ohne dass sich die Kamera/das Board tatsächlich gedreht hat.
- Alternativen: (a) Reihenfolge nachträglich im Code heuristisch angleichen
  (z.B. per Positions-/Abstandsvergleich zwischen erster/letzter Ecke L↔R
  umsortieren), (b) neues asymmetrisches Muster drucken (z.B. 9x6
  Innenecken).
- Begründung: (b) gewählt für den finalen Kalibrier-Datensatz — vermeidet
  die Fehlerquelle strukturell statt mit fragiler Heuristik, die bei jeder
  neuen Pose erneut greifen müsste und schwer zu testen ist. Für die
  heutigen Sanity-Checks (Belichtung, Verzeichnung, reine
  Erkennbarkeitsprüfung) bleibt das vorhandene 7x7-Muster nutzbar, da dort
  keine L/R-Punktkorrespondenz gebraucht wird. Vor der eigentlichen
  `stereoCalibrate`-Datenaufnahme: neues Muster (9x6, ausgemessen, mit
  weißem Rand) drucken.

## 2026-09-03 — Verzeichnung & L/R-Helligkeit über 3 Board-Posen quantifiziert

- Kontext: 3 Testaufnahmen mit dem 7x7-Schachbrett bei `--shutter 10000
  --gain 1.0 --awbgains 1.0,1.0 --denoise off`: (1) 1m, frontal/mittig,
  (2) Ecke oben-links, leicht gekippt, (3) weit rechts, nah am Bildrand,
  stark gekippt. Alle Ecken via `cv2.findChessboardCornersSB` erkannt.
- Verzeichnung: Für jede der 7 Ecken-Reihen eine Gerade gefittet (Total-
  Least-Squares) und die maximale senkrechte Abweichung der 7 Punkte davon
  gemessen (physische Reihen sind exakt gerade, Abweichung im Bild = Indiz
  für Linsenverzeichnung). Ergebnis: 0,11px (Pose 1) / 0,27px (Pose 2) /
  0,37px (Pose 3, am nächsten zum Bildrand) — durchgängig sehr klein.
  Einschränkung: keine der Posen lag exakt in der äußersten Bildecke, für
  eine vollständige Verzeichnungs-Charakterisierung (relevant für die
  radialen Distortion-Koeffizienten in `calibrateCamera`) reicht das nicht,
  ist aber ein positives erstes Signal (Objektiv scheint wenig verzeichnet).
- L/R-Helligkeit: Mittelwert-Differenz nur auf der Board-Bounding-Box (statt
  ganzes Bild wie in Tag 2): 1,2 % / 1,2 % / 2,9 % über die 3 Posen — klar
  kleiner als der ~6 % Szenen-Unterschied aus Tag 2. Erklärung: dort wurde
  die gesamte, unterschiedlich beleuchtete Szene verglichen; hier ein
  kleiner Bildausschnitt mit nahezu identischem Inhalt in L/R. Für Phase 2
  (Feature-Matching) unkritisch.
- Nebenbefund (technisch, relevant für `src/calibration`):
  `cv2.CALIB_CB_FAST_CHECK` lehnte Pose 3 (großes, stark gekipptes Brett)
  faelschlich ab (falsches Negativ) — ohne das Flag bzw. mit
  `cv2.findChessboardCornersSB(..., flags=cv2.CALIB_CB_EXHAUSTIVE)`
  zuverlässig erkannt. Für die spätere Kalibrier-Implementierung
  `findChessboardCornersSB` ohne `FAST_CHECK` verwenden, siehe
  `cal/check_corners.py` als Referenzimplementierung.

## 2026-09-03 — Schachbrett auch bei ~2m Distanz noch erkennbar

- Kontext: 4. Testpose bei ca. 2m Distanz (obere Grenze des Zielarbeits-
  bereichs, siehe CLAUDE.md), frontal. Alle 49 Ecken in L und R erkannt,
  Reihenfolge zwischen L/R konsistent.
- Messung: Board (7x7 Innenecken) nur noch ~63x62px groß im Bild, das
  entspricht ~10,5px pro Feld (bei 24mm realer Feldkantenlänge).
- Einschätzung: Erkennung funktioniert trotz geringer Pixelgröße
  zuverlässig, aber die Subpixel-Genauigkeit der Eckenlokalisierung dürfte
  bei so wenigen Pixeln/Feld geringer sein als bei näheren Distanzen —
  keine Präzisionsmessung dazu gemacht, nur Plausibilitätsprüfung. Für
  PoC-Niveau (siehe CLAUDE.md) ausreichend; bei der finalen
  Kalibrierdatensammlung ggf. mehr Aufnahmen im Nah-/Mittelbereich
  gewichten und Fernbereich (~2m) nicht übergewichten, da unpräziser.
- Noch offen: Nahbereich (~0,3m) nicht getestet.

## 2026-09-04 — Schachbrett wird zugeschnitten statt neu gedruckt (7×7 → 6×7 Innenecken)

- Kontext: Tag-3-Befund (Ecken-Reihenfolge-Mehrdeutigkeit bei symmetrischem 7×7-Muster) erfordert ein asymmetrisches Muster für `stereoCalibrate`. Ursprünglich vorgemerkt: neues 9×6-Muster drucken (CHECKLIST.md Tag 4).
- Alternativen: (a) neues Muster drucken, (b) vorhandenes 8×8-Feld-Board um eine äußere Feldreihe beschneiden → 8×7 Felder = 6×7 Innenecken (asymmetrisch).
- Begründung: (b) gewählt. Die Mehrdeutigkeit entsteht durch gleiche Zeilen-/Spaltenzahl, nicht durch die konkrete Größe 9×6 — jedes asymmetrische Format löst das Problem. Zuschneiden spart Druck/Papier und die erneute Unsicherheit der Quadratgröße eines neuen Ausdrucks; das vorhandene Board (Kantenlänge nominell 24mm, Verifikation offen) wird weiterverwendet.
- Bedingungen: Schnitt muss exakt entlang einer Feldgrenze liegen (nicht mitten durch eine Reihe), damit alle verbleibenden Felder volle 24mm-Quadrate bleiben; möglichst etwas weißen Rand stehen lassen. Nach dem Schnitt Erkennung (6×7 statt 7×7, konsistent zwischen L/R) mit `findChessboardCornersSB` gegenchecken.
- Konsequenz für Code: `patternSize` in `src/calibration` künftig `(6, 7)` (oder `(7, 6)`, je nach Achsenkonvention) statt `(7, 7)`.

## 2026-09-04 — Namenskonvention `data/calibration_images/` festgelegt

- Kontext: Seit Tag 3 offener Punkt aus CHECKLIST.md.
- Entscheidung: `left_NNN.png` / `right_NNN.png`, `NNN` = 3-stelliger, nullgepaddeter Index als gemeinsame Paar-ID zwischen L/R (kein Timestamp-Matching nötig). Zusätzlich Begleit-Manifest `data/calibration_images/manifest.csv` mit Spalten `index,distanz_m,notiz,shutter,gain,timestamp` für Pose-/Settings-Metadaten je Aufnahme.
- Alternativen: Pose-Label direkt im Dateinamen (z.B. `left_1m_frontal.png`) — verworfen, da unübersichtlich bei vielen Aufnahmen und schlecht script-freundlich (Sortierung, `glob`-Paarbildung).
- Begründung: Index-basierte Dateinamen bleiben eindeutig sortierbar und einfach programmatisch zu paaren. Manifest-CSV folgt demselben Muster wie `cal/opt_calib.csv` (bereits etabliert für Ad-hoc-Settings-Tests), jetzt für den finalen Kalibrier-Datensatz.

## 2026-09-04 — Stuhllehnen-Montage für erste Tests akzeptiert

- Kontext: Board aktuell nur an Stuhllehne positioniert/geklemmt (siehe Tag-3-Checkliste), kein fester Untergrund.
- Entscheidung: Für erste Software-/Erkennungstests akzeptiert, da die Fläche subjektiv ausreichend eben ist. Feste Montage auf harter, ebener Unterlage bleibt offen für den finalen Kalibrier-Datensatz.
- Begründung: Kein Blocker fürs Aufsetzen der Kalibrier-Pipeline (Phase 1 startet mit Code-Struktur, nicht mit finalen Messdaten). Risiko: leichte Wölbung/Instabilität könnte in den finalen Kalibrierbildern minimale Ungenauigkeit einbringen — vor der eigentlichen finalen Datenaufnahme nochmal prüfen.

## 2026-09-04 — Methodenwechsel: map-based → einfache Visuelle Odometrie (VO) ohne Loop-Closure

- Kontext: Ursprünglicher Plan (siehe `projektbrief.md` Stand 2026-08-31, mit Betreuer-Kontext Prof. Borchers-Tigasson): map-based Ansatz — Referenzpunkte im Testraum vorher vermessen, Pose zur Laufzeit per PnP relativ dazu bestimmt, SLAM explizit nur als Ausblick. Beim Start der Referenzpunkt-Vermessung (Phase 2) wurde die Grundsatzfrage nochmal aufgeworfen, aus zwei Gründen: (1) weniger Zeit verfügbar als ursprünglich angenommen (Projektbrief ging von Vollzeit in den Semesterferien aus), (2) Realismus-Argument — ein echter Rover (ERC-Kontext) hätte in einer neuen Umgebung nicht die Möglichkeit, vorher irgendetwas von Hand zu vermessen.
- Alternativen abgewogen:
  - (a) **Map-based (ursprünglicher Plan)**: einfachere Algorithmik (Einzelbild-`solvePnP` gegen bekannte Punkte, kein Drift-Problem), aber braucht vorherige Vermessung mehrerer Landmarken — realitätsfern für ein autonomes Rover-Szenario.
  - (b) **Volles SLAM** (Loop-Closure, Bundle Adjustment, laufender Kartenaufbau): realistischste Abbildung eines echten autonomen Systems, aber der Implementierungsaufwand ist um Größenordnungen höher (vergleichbar mit mehrjährigen Forschungsprojekten wie ORB-SLAM3) — für die verbleibende Zeit nicht machbar.
  - (c) **Einfache Visuelle Odometrie (VO) ohne Loop-Closure**: zeitliches Feature-Matching zwischen aufeinanderfolgenden Aufnahmen statt gegen eine statische Punktliste, 3D-Relativbewegung wird geschätzt (3D-3D-Punktwolken-Alignment oder `solvePnP` mit 3D-Punkten aus dem Vorframe) und zu einer Trajektorie aufsummiert (`Pose_t = Pose_t-1 · Relativbewegung`). Kein Kartenaufbau, keine Wiedererkennungs-/Korrekturlogik, keine globale Optimierung.
- Begründung: (c) gewählt. Nutzt fast dieselben Kernbausteine, die ohnehin geplant waren (ORB-Feature-Detektion, Stereo-Triangulation für Tiefe) — neu ist im Wesentlichen nur das zeitliche Matching (statt gegen eine gespeicherte Punktliste) und die Pose-Verkettung. Dadurch entfällt die aufwendige Mehrpunkt-Vermessung des Testraums fast komplett (nur noch ein einziger Startpunkt nötig). Deutlich realistischer für das Rover-Zielszenario als map-based, deutlich machbarer als volles SLAM in der verbleibenden Zeit. Mit etablierten Metriken aus der SLAM-Literatur (ATE/RPE) sauber und wissenschaftlich anschlussfähig evaluierbar.
- Akzeptierte Einschränkung: ohne Loop-Closure/globale Optimierung akkumulieren kleine Schätzfehler jedes Schritts unkorrigiert über die Strecke (Drift, wächst mit Weglänge/Framezahl). Wird in der Arbeit offen als Limitation behandelt und quantifiziert (ATE/RPE gegen Maßband-Wegpunkte), nicht behoben. Analogie zu echten Mars-Rovern: auch die korrigieren VO-Drift periodisch über externe Referenzen (Orbitalbild-Abgleich, Sonnensensor) — komplett referenzfreie Navigation ist auch dort nicht der Stand der Technik, insofern ist "kein einziger Referenzpunkt" auch für dieses Projekt nicht ganz richtig: ein Startpunkt bleibt nötig.
- Konsequenzen für Repo/Code:
  - `data/reference_points.yaml`: Rolle geändert von "Laufzeit-Karte für PnP" zu "Startpunkt-Ursprung (Pflicht) + optionale Ground-Truth-Wegpunkte entlang der Testroute (nur für die Auswertung, nicht vom Algorithmus genutzt)". Format unverändert.
  - `src/capture`: muss künftig Aufnahme-Sequenzen an unterschiedlichen, sich bewegenden Kamerapositionen unterstützen (Stop-and-Shoot: Kamera bewegen, kurz anhalten, Aufnahme), nicht nur eine Einzelaufnahme mit fix montierter Kamera wie bisher in Tag 1–4 getestet.
  - `src/localization`: erweitert sich um zeitliches Feature-Matching (Frame_t-1 ↔ Frame_t) und Pose-Verkettungslogik, zusätzlich zur ohnehin geplanten Stereo-3D-Triangulation.
  - `src/evaluation`: Validierungsmethodik wechselt von "Posefehler gegen Referenzpunkte" zu "Trajektorienfehler über eine gemessene Wegstrecke" (ATE/RPE-artige Metriken).
  - `CLAUDE.md` und `projektbrief.md` entsprechend aktualisiert (2026-09-04).
- Offen/zu klären: diese Grundsatzentscheidung weicht vom ursprünglich mit Betreuer-Kontext dokumentierten Projektbrief ab — sollte bei nächster Gelegenheit mit Prof. Borchers-Tigasson kurz rückgespiegelt werden, auch wenn inhaltlich fachlich gut begründbar.

## 2026-09-04 — Projekt-Prinzip: erst funktionale Pipeline, dann Fine-Tuning

- Kontext: Mehrere offene Tag-4-Punkte (Beleuchtung optimieren, Nahbereichstest, ggf. spätere Fokus-Feinjustage) sind Präzisions-/Vollständigkeits-Aufgaben. Der aktuelle Prototyp-Aufbau (Nagel-Halterung, Sessellehnen-Montage) ist ohnehin nicht auf Endgenauigkeit ausgelegt.
- Entscheidung: Priorität ab jetzt auf einer durchgängig funktionierenden Kalibrier-/Lokalisierungs-Pipeline (Ende-zu-Ende), auch mit bekannten Ungenauigkeiten in Mechanik/Beleuchtung/Fokus/Posenabdeckung. Exaktheit/Fine-Tuning (mechanische Stabilisierung, Beleuchtungsoptimierung, vollständige Distanz-/Posenabdeckung) wird auf eine spätere Phase verschoben, nachdem die Pipeline grundsätzlich steht.
- Begründung: Für PoC-Niveau (siehe CLAUDE.md) ist eine funktionierende, nachvollziehbare Pipeline wichtiger als frühzeitige Präzisionsoptimierung an einem ohnehin noch provisorischen Aufbau — Optimierungsaufwand an der aktuellen Halterung wäre teilweise hinfällig, sobald eine stabilere Halterung existiert.
- Risiko/Konsequenz: Ergebnisse aus dieser Phase (Reprojection Error etc.) sind nicht final aussagekräftig und müssen bei der finalen Datenaufnahme wiederholt werden — bewusst in Kauf genommen, sollte in der schriftlichen Arbeit als Zwischenstand markiert werden, nicht als Endergebnis.

## 2026-09-04 — Fokus: keine manuelle Verstellmöglichkeit gefunden

- Kontext: Tag-4-Punkt "Fokusring sichern" — beim Versuch, den Fokus zu prüfen/fixieren, keine zugängliche Einstellmöglichkeit am Kameramodul gefunden; Fokus lässt sich nicht manuell verschieben.
- Konsequenz: Punkt als nicht-aktionabel akzeptiert. Ob der Werksfokus optimal für den Zielbereich 0,3–2m ist, bleibt ungeprüft — falls später Schärfeprobleme auffallen (z.B. auffällig hoher Reprojection Error oder sichtbar unscharfe Ecken bei der Subpixel-Verfeinerung), Arducam-B0266/OV9281-Datenblatt auf Fixfokus-Spezifikation prüfen.

## 2026-09-04 — Quadratgröße verifiziert: 24mm

- Kontext: Tag-4-Punkt, mit Lineal/Messschieber nachgemessen statt dem Druck zu vertrauen.
- Ergebnis: 24mm bestätigt — Sollwert aus dem Druck stimmt mit der Realität überein. Wert für `src/calibration` (Skalierung der 3D-Objektpunkte `objp`) direkt verwendbar.

## 2026-09-07 — 2D-Top-Down-Karte als zusätzlicher Visualisierungs-Output

- Kontext: Beim konzeptionellen Durchgehen der VO-Schritte (siehe
  Methodenwechsel-Eintrag 2026-09-04) aufgekommene Frage: lässt sich aus den
  ohnehin berechneten VO-Daten eine einfache 2D-Karte erzeugen?
- Entscheidung: Ja — als zusätzlicher, rein nachgelagerter
  Visualisierungs-/Auswertungs-Output. Die (x, z)-Positionen der
  verketteten Kamera-Posen (Schritt 5 der VO) ergeben direkt einen
  Top-Down-Pfad; optional werden zusätzlich die triangulierten 3D-Feature-
  Punkte (Schritt 2) auf die x-z-Ebene projiziert und mit eingezeichnet.
- Alternativen: (a) keine Kartendarstellung, nur Trajektorien-/Fehlerplots
  (Zahlenwerte); (b) Karte als Laufzeitkomponente, die zur Pose-Korrektur
  genutzt wird — verworfen, da das faktisch (Teil-)SLAM mit Kartennutzung
  wäre und damit gegen die Scope-Abgrenzung in CLAUDE.md verstößt.
- Begründung: Die Karte wird ausschließlich aus bereits vorliegenden VO-
  Ergebnissen nachträglich erzeugt, nicht zur Laufzeit von der Lokalisierung
  genutzt (kein Loop-Closure, kein Bundle Adjustment, keine
  Neupositionierung anhand der Karte) — bleibt damit innerhalb der in
  CLAUDE.md festgelegten Abgrenzung ("kein volles SLAM"). Da Fehler
  unkorrigiert akkumulieren, macht die Karte den Drift zusätzlich
  anschaulich sichtbar (z.B. eigentlich parallele Wände laufen auseinander)
  — inhaltlich ein Plus für die Diskussion der Limitation in der Arbeit.
- Konsequenzen für Repo/Code: Einordnung als Skript in `scripts/`
  (z.B. `plot_trajectory_map.py`) bzw. `src/evaluation/`, nicht in
  `src/localization/` — kein Bestandteil des Lokalisierungsalgorithmus.

## 2026-09-07 — RANSAC in estimate_relative_pose_ransac() ergänzt (Ausreißer in 3D-3D-Korrespondenzen)

- Kontext: Beim ersten End-to-End-Test von `vo_pipeline.py` (synthetische Bildsequenz, bekannte Kamerabewegung) wich die geschätzte Pose deutlich von der bekannten Ground Truth ab (5° Rotationsfehler statt ~0°, Y/Z-Translation ungleich Null statt ~0). Diagnose: von 173 zeitlichen 3D-3D-Korrespondenzen waren ~39% Ausreißer. Weitere Diagnose (auf Rückfrage): der Fehler entsteht bereits beim Stereo-Matching (Schritt L↔R) — schon bei einem einzelnen Frame hatten 39 von 256 Stereo-Matches (15%) eine falsche Disparität, trotz korrekt funktionierender Einzelmodule (jede Stufe für sich exakt getestet). Ursache: `match_stereo_pairs()`/`match_temporal_features()` nutzen reinen Deskriptor-Abgleich ohne Kreuzvalidierung gegen die Geometrie über alle Punkte hinweg — bei ähnlich aussehenden Merkmalen (hier: gleichartige synthetische Kreise) sind Fehlzuordnungen normal, nicht nur ein Artefakt der Testszene.
- Alternativen: (a) einzelne Matching-Stufen mit szenenspezifischen Heuristiken nachbessern, (b) Ausreißer-Robustheit zentral in `pose_estimation.py` (RANSAC) ergänzen, (c) Problem für den PoC-Stand akzeptieren und nur dokumentieren.
- Begründung: (b) gewählt. Alle vorherigen Fehler (Stereo- und zeitliches Matching) laufen an dieser Stelle zusammen — ein robuster Schätzer hier fängt Fehlzuordnungen unabhängig von ihrer Quelle ab, ohne szenenspezifische Annahmen in den Matching-Stufen. Standardlösung in der VO/SLAM-Literatur. `estimate_relative_pose()` (reiner Kabsch) bleibt als getesteter Kern bestehen; `estimate_relative_pose_ransac()` (neue Funktion) zieht wiederholt zufällige 3-Punkt-Minimalstichproben, zählt Inlier unter einem Distanz-Schwellwert, und verfeinert R,t per Kabsch auf der größten Inlier-Menge. `vo_pipeline.py` nutzt jetzt ausschließlich die RANSAC-Variante.
- Ergebnis nach der Änderung: derselbe End-to-End-Test (synthetische Sequenz, bekannte laterale Bewegung) liefert Rotationsfehler <0,1° und Translationsfehler im mm-Bereich über mehrere Frames (siehe `scripts/check_vo_pipeline.py`), statt der vorherigen deutlichen Abweichung.
- Offen/Schwellwert-Begründung: `inlier_threshold` default 2cm ist ein Startwert für den Zielbereich 0,3–2m (siehe CLAUDE.md), noch nicht gegen echte Messungen/Rauschcharakteristik validiert — bei der ersten echten Kalibrier-/VO-Datenaufnahme (Phase 1/2) prüfen und ggf. anpassen. `max_iterations` default 200 gibt bei bis zu ~50% Ausreißeranteil eine sehr hohe Erfolgswahrscheinlichkeit (mind. eine saubere 3-Punkt-Stichprobe), noch nicht gegen echte Ausreißerquoten kalibriert.

## 2026-09-04 — Nahbereichstest (~0,3m) verschoben

- Kontext: Tag-4-Punkt, aktueller Prototyp-Aufbau (Sessellehnen-Montage, Nagel-Halterung) lässt sich nicht ohne größeren Umbau für Nahbereich-Aufnahmen anpassen.
- Entscheidung: Verschoben auf einen späteren Zeitpunkt (nach stabilerer Halterung oder im Rahmen des späteren Fine-Tunings, siehe Projekt-Prinzip oben). Kein Blocker für den funktionalen Kalibrier-Code — Nahbereichsabdeckung ist eine Vollständigkeitsfrage, keine Grundvoraussetzung für eine erste funktionierende Pipeline.

## 2026-09-07 — Erste echte Kalibrierung: 20 Aufnahmen, Baseline-Plausibilitätscheck bestanden

- Kontext: Erste echte Kalibrieraufnahme-Session auf dem Pi (statt bisher nur synthetischer Testdaten). 20 Stereo-Bildpaare mit dem 6×7-Brett, Distanz 0,5–2m, gemischt mit horizontaler/vertikaler Kippung und variierender Position im Bild (siehe `data/calibration_images/manifest.csv`).
- Nebenbefund (Bugfix, siehe Commit `845dfa0`): beim ersten Testlauf auf dem Pi (OpenCV 4.10.0) schlug `test_corners.py` fehl — `cv2.findChessboardCornersSB` liefert dort `(N,1,2)` statt `(N,2)` wie auf dem Mac-Dev-System (OpenCV 5.0.0). Bisher ausschließlich auf dem Mac getestet, daher unbemerkt. `find_checkerboard_corners()` normalisiert die Form jetzt intern, unabhängig von der OpenCV-Version. Lehre: sobald Hardware-nahe Module entstehen, auf beiden Systemen testen, nicht nur dem Dev-Rechner.
- Ergebnis (`scripts/run_calibration.py`, `results/calibration/2026-09-07_calibration.yaml`):
  - 19 von 20 Bildpaaren nutzbar (Bild 15 verworfen: Brett stand zu weit oben, nur ein schmaler Streifen des Musters im Bild — Muster in keiner Hälfte gefunden. Per Live-Feedback im Aufnahme-Skript sofort bemerkt und bei der Distanz/Pose korrigiert, keine nachträgliche Fehlersuche nötig).
  - Intrinsics-Reprojection-Error: L=0,288px, R=0,293px (sub-pixel, gut).
  - Extrinsics-Reprojection-Error: 0,707px.
  - Baseline aus `stereoCalibrate`: **61,36mm** vs. Maßband-Referenz **60mm** (siehe 2026-09-02) → **Abweichung ~2,3%**.
- Einschätzung: Erster echter End-to-End-Durchlauf der kompletten Kalibrier-Pipeline (bisher nur an synthetischen Daten mit bekannter Ground Truth verifiziert) bestätigt, dass sie auch auf echten Kamerabildern sinnvolle, plausible Ergebnisse liefert — kein Beleg für hohe Präzision (Maßband-Referenz selbst ist PoC-Niveau, siehe CLAUDE.md), aber ein starkes Indiz, dass keine grobe systematische Fehlfunktion vorliegt. Nächster Schritt laut Roadmap: erste Tiefenmessung vs. Maßband (Phase 1, noch offen).

## 2026-09-07 — Erste Tiefenmessung vs. Maßband: 6–7,5% Abweichung, akzeptiert für den aktuellen Prototyp-Stand

- Kontext: Validierung laut CLAUDE.md-Roadmap Phase 1 ("erste Tiefenmessung vs. Maßband"). Neues Skript `scripts/measure_depth.py`: nimmt eine unabhängige Stereo-Aufnahme (nicht Teil der Kalibrierbilder) bei einer frisch mit Maßband gemessenen Distanz auf, rektifiziert sie mit dem gespeicherten Kalibrierergebnis, trianguliert die Schachbrett-Ecken und vergleicht die mittlere berechnete Tiefe mit der Maßband-Distanz.
- Messungen (Board frontal, Distanz bis zur Linse gemessen, siehe `results/measurements/2026-09-07_depth_validation_*`):
  - 1,39m (±5mm) gemessen → 1,285m berechnet → **-104,7mm (-7,5%)**, Streuung über 42 Eckpunkte nur 6,5mm (Board also sauber/flach erfasst, kein Verwackeln).
  - 0,70m gemessen → 0,657m berechnet → **-43,1mm (-6,2%)**, Streuung 5,9mm.
- Analyse: Der *relative* Fehler ist zwischen beiden Distanzen ähnlich (-7,5% / -6,2%), der *absolute* Fehler dagegen sehr unterschiedlich (10,5cm vs. 4,3cm) — spricht eher für einen systematischen Maßstabsfehler in der Kalibrierung als für einen falschen Mess-Referenzpunkt (der hätte einen ähnlichen *absoluten* Versatz erzeugen müssen, zumal beide Male konsistent bis zur Linse gemessen wurde). Widerspricht sich aber teilweise mit dem Baseline-Befund von oben (dort +2,3%, hier -6 bis -7,5% — bei einem reinen Quadratgrößen-Skalierungsfehler müssten beide in dieselbe Richtung abweichen). Ursache nicht abschließend geklärt.
- Wahrscheinlichster Kandidat: der bereits in der Tag-4-Checkliste dokumentierte Risikopunkt — das Schachbrett ist nur auf Karton geklebt und an der Stuhllehne befestigt, keine feste Montage auf harter, ebener Unterlage; eine leichte Wölbung würde die Eckenabstände systematisch verzerren und ließe sich nicht als einfacher, konsistenter Skalierungsfaktor beschreiben. Nicht verifiziert, nur die naheliegendste Erklärung.
- Entscheidung: Für den aktuellen Stand akzeptiert, keine weitere Fehlersuche jetzt. Begründung (User): angesichts des rudimentären Aufbaus (weder Kameras noch Schachbrett exakt eben montiert) ist eine Abweichung von 6–7% ein nachvollziehbares und verkraftbares Ergebnis, keine grobe Fehlfunktion. Passt zum Projekt-Prinzip "erst funktionale Pipeline, dann Fine-Tuning" (siehe 2026-09-04) — Ursachenklärung (Board-Wölbung pruefen, ggf. neu montieren, mehr/bessere Kalibrieraufnahmen) wird auf die für Projektende vorgesehene Fine-Tuning-Phase verschoben, kein Blocker für den Fortschritt zu Phase 2 (Lokalisierung/VO).
- Für die Arbeit: als quantifizierter Ist-Stand der Tiefengenauigkeit mit PoC-Aufbau dokumentiert (6–7,5% bei 0,7–1,4m), nicht als Endergebnis. Gute, ehrliche Ausgangsbasis für die spätere Diskussion, wie viel die Fine-Tuning-Phase (feste Montage, mehr Kalibrieraufnahmen) tatsächlich verbessert.

## 2026-09-08 — Merkmalsdichte auf natürlicher Szene geprüft: vorhanden, aber sehr ungleich verteilt

- Kontext: `detect_features()` (ORB, `src/localization/features.py`) war bisher ausschließlich an synthetischen Bildern und an Fotos des Kalibrier-Schachbretts getestet — nie an einer echten Szene mit natürlichen Objekten, wie sie die eigentliche VO später verarbeiten soll. Vor der ersten echten VO-Sequenzaufnahme als schneller Sanity-Check geprüft: eine einzelne Stereo-Aufnahme vom Testraum (ohne Schachbrett) mit `scripts/check_features.py` ausgewertet.
- Bilder: `results/measurements/2026-09-08_feature_density_check/room_natural_L.png` (Rohbild, linke Kamera) und `.../features_annotated.png` (mit eingezeichneten ORB-Keypoints).
- Ergebnis: 465 Merkmale gefunden (nahe am Limit von 500) — grundsätzlich ausreichend Textur im Raum vorhanden. Verteilung aber sehr ungleichmäßig: der Großteil der Punkte sitzt auf den Kanten einer Kommode und auf Vorhangfalten; große, glatte Flächen (Wand, Bettwäsche im Vordergrund) liefern fast keine Merkmale.
- Einschätzung: Kein Blocker, aber ein reales Risiko für die VO-Sequenz — verlässt die texturreiche Kommode/Vorhang-Region den Bildausschnitt, könnte dem zeitlichen Feature-Matching (Frame_t-1↔t) die Korrespondenzgrundlage zu großen Teilen fehlen. Konsequenz für die Aufnahme der Testroute: Kamera bewusst so ausrichten, dass die texturreichen Objekte durchgehend im Bild bleiben, nicht auf leere Wand-/Bettflächen zielen.
