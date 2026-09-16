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

## 2026-09-08 — Erste echte VO-Sequenz End-to-End: funktioniert, mit erwartetem Drift + einem erklärten Ausreißer

- Kontext: Erster echter End-to-End-Test der kompletten `vo_pipeline` (bisher nur an synthetischen Daten verifiziert, siehe 2026-09-07). Testroute: reine Lateralbewegung der Kamera entlang eines Tisches (~1,2m), 20cm-Schritte per Massband, Kamera-Ausrichtung sollte konstant bleiben (kein Nachschwenken). 7 Bildpaare, `data/vo_sequences/2026-09-08_tisch_translation/`. Neues Orchestrator-Skript `scripts/run_vo_sequence.py` (Kalibrierung laden → Sequenz rektifizieren → `run_vo_pipeline()` → Vergleich mit `data/reference_points.yaml`), analog zu `run_calibration.py`.
- Ergebnis (`results/measurements/2026-09-08_vo_sequence_test/trajectory.yaml`):
  - Frames 0–5 (0 bis 100cm): Bewegungsrichtung durchgehend korrekt, Fehler wächst moderat mit der Strecke (5,5cm bei 20cm → 23,2cm bei 100cm, ca. 15-25% relativ) — typisches, unkorrigiertes VO-Drift-Verhalten, keine grobe Fehlfunktion.
  - Frame 6 (120cm): deutlicher Ausreißer, geschätzt -2,38m statt -1,2m (147cm Fehler).
- Ursachenanalyse (Diagnose-Skript, Stereo-3D-Punkte / zeitliche Matches / RANSAC-Inlier pro Frame-Übergang): Merkmalszahl bricht ab Frame 4 (80cm) stark ein und stürzt bei Frame 6 auf nur noch 18 triangulierte 3D-Punkte bzw. 4 RANSAC-Inlier ab (0→1: 208 Punkte/39 Inlier; 5→6: 18 Punkte/4 Inlier). Mit nur 4 Punkten ist die Kabsch-Pose-Schätzung praktisch unterbestimmt, daher der Ausreißer.
- Zwei plausible, sich nicht ausschließende Ursachen für den Merkmalsschwund in der Ferne:
  1. Die einzige texturreiche Zone der Szene (Kommode/Vorhang, siehe Merkmalsdichte-Check oben) wandert mit fortschreitender Seitwärtsbewegung an den Bildrand und wird kleiner im Bild.
  2. (User-Beobachtung) Die Kamera-Ausrichtung wurde nach jedem manuellen Versetzen nicht immer exakt gleich nachjustiert — kleine Winkelfehler wirken sich in größerer Entfernung von der Startposition stärker auf die Merkmalsüberlappung zwischen aufeinanderfolgenden Frames aus.
  - Nicht getrennt, da beide zum selben Symptom (weniger valide zeitliche Korrespondenzen mit wachsender Distanz) führen und für den aktuellen Zweck nicht auseinandergehalten werden müssen.
- Entscheidung: Für den aktuellen Stand akzeptiert, keine weitere Fehlersuche jetzt. Begründung (User): Ziel ist erst ein grundsätzlich funktionsfähiger Stand, Fine-Tuning (u.a. Kamera-Ausrichtung/Framing über die ganze Route stabil halten) kommt in einer späteren Phase. Passt zum Projekt-Prinzip "erst funktionale Pipeline, dann Fine-Tuning" (siehe 2026-09-04).
- Für die Arbeit: erster quantifizierter Beleg, dass die komplette VO-Kette (Kalibrierung → Rektifizierung → Feature-Detektion → Stereo-Matching/Triangulation → zeitliches Matching → RANSAC-Pose-Schätzung → Trajektorien-Verkettung) auch auf echten Kamerabildern lauffähig ist und plausible Ergebnisse liefert, mit einem sauber diagnostizierten Fehlerfall als Beispiel für die Grenzen des Ansatzes bei unzureichender Merkmalsüberlappung — guter Diskussionspunkt für die Limitations-Sektion.
- RANSAC-Parameter (`inlier_threshold`=2cm, `max_iterations`=200) unverändert gelassen: das Problem hier ist Merkmalsknappheit (zu wenige Korrespondenzen insgesamt), kein Schwellwert-Tuning-Problem — RANSAC kann keine Pose aus 4 Punkten robust retten, unabhängig vom Threshold.

## 2026-09-08 — Ausblick: mobiler Wagen mit periodischer Live-VO als finaler Validierungsaufbau

- Kontext: Idee (User) für den finalen Validierungsaufbau, nachdem die Stop-and-Shoot-Sequenz heute grundsätzlich funktioniert hat: die Kamera auf eine rollende, ggf. 3D-gedruckte Halterung montieren, damit frei durch den Raum fahren und dabei automatisch im 1-2s-Takt Aufnahmen machen + live auswerten (laufende Trajektorien-Ausgabe statt nachträglicher Batch-Verarbeitung).
- Softwareseitig kein Neubau: `run_vo_sequence.py` verarbeitet aktuell eine fertige Bildserie im Batch; für Live-Betrieb müsste das nur auf "aufnehmen → sofort verarbeiten → Zwischenstand ausgeben" umgestellt werden, die Kernbausteine (Feature-Detektion, Matching, Pose-Schätzung, Trajektorien-Verkettung) bleiben unverändert.
- Grobe Performance-Indikation (nicht als belastbare Messung zu verstehen): kompletter 7-Frame-Batch-Durchlauf heute auf dem Pi brauchte 3,9s total (inkl. Python-/Import-Overhead) — reine Pro-Frame-Verarbeitung eher ~0,3–0,5s. Aufnahme-Latenz (`rpicam-still`, aktuell 300ms-Timeout + Subprocess-Overhead) ist separat zu benchmarken, bevor ein Takt (1s vs. 2s) festgelegt wird.
- Der Wagen/3D-Druck-Teil ist ein eigenständiges mechanisches Vorhaben (Design, Druck, Montage von Kamera + mobiler Stromversorgung), unabhängig vom Code.
- Entscheidung: als Ausblick für den finalen Validierungsaufbau festgehalten, nicht jetzt umgesetzt. Nächster sinnvoller Schritt bleibt zunächst, die heute gefundenen Schwachstellen (Framing/Kamera-Ausrichtung über die ganze Route stabil halten) in einer saubereren Stop-and-Shoot-Sequenz zu adressieren, bevor in Mobilität/Live-Betrieb investiert wird.

## 2026-09-10 — Tag 7 (Wiederholungssequenz) zurückgestellt; stattdessen Top-Down-Trajektorienkarte

- Kontext: Tag 7 war als zweite VO-Sequenz geplant (sauberes Framing gegen den Merkmalsschwund-Ausreißer aus Tag 6, plus eine erste Sequenz mit Rotation). Rückfrage/Bewertung (User): eine Wiederholungsmessung jetzt bewertet er als unnötig — der Tag-6-Test war grundsätzlich funktional (Frames 0–5 zeigen normalen, erwarteten Drift), der Ausreißer bei Frame 6 ist bereits ursachenerklärt (Merkmalsschwund) und nicht das eigentliche Ziel der nächsten Iteration.
- Alternativen: (a) Tag 7 wie geplant durchführen, um die Framing-Hypothese direkt zu testen; (b) Tag 7 zurückstellen, bis ein saubererer Aufbau/Testraum verfügbar ist, und stattdessen zuerst offene funktionale Lücken schließen (hier: `plot_trajectory_map.py`, siehe 2026-09-07-Eintrag).
- Entscheidung: (b). Priorität liegt auf einem vollständig funktionalen Gesamtstand über alle Phasen hinweg, bevor in Wiederholungsmessungen/Feinjustage investiert wird — deckt sich mit dem bereits etablierten Projektprinzip "erst funktionale Pipeline, dann Fine-Tuning" (siehe 2026-09-04 und 2026-09-08-Eintrag zum Tag-6-Ausreißer). Optimierungs-/Wiederholungsmessungen (Tag-7-Punkte: zweite Translationssequenz, Rotationssequenz, `reference_points.yaml`-Format für mehrere Sequenzen) werden erst angegangen, sobald ein sauberer Aufbau und ein besserer Testraum verfügbar sind.
- Konsequenz: `scripts/plot_trajectory_map.py` implementiert (2D-Top-Down-Plot der VO-Trajektorie, optional gegen `reference_points.yaml`-Ground-Truth, mit `--exclude-frames` für bereits diagnostizierte Ausreißer wie Frame 6 aus Tag 6 — diese werden separat markiert, nicht stillschweigend entfernt). Karte für die Tag-6-Sequenz erzeugt: `results/measurements/2026-09-08_vo_sequence_test/trajectory_map.png`. Die Tag-7-Punkte in `CHECKLIST.md` bleiben als zurückgestellt (nicht verworfen) stehen.

## 2026-09-10 (Update) — Scope-Entscheidung: Live-VO wird konkret umgesetzt (inkl. Rotation), ROS bleibt nur strukturell vorbereitet

- Kontext: Rückfrage im Anschluss an den obigen Tag-7-Eintrag, ob "Live-Messung" und "ROS-Datenaustausch" (vom User als nächste Schritte genannt) wie in der bisherigen Ausblick-Notiz (2026-09-08, mobiler Wagen) nur konzeptionell bleiben, oder tatsächlich implementiert werden sollen — beides weicht vom bisher in `CLAUDE.md` festgelegten Scope ab (Stop-and-Shoot statt Live; keine echte ROS2-Integration, nur strukturelle Vorbereitung).
- Entscheidung (User):
  - **Live-VO**: wird jetzt konkret umgesetzt, geplant für morgen (2026-09-11) — inkl. Rotationstest (nicht nur reine Translation wie in Tag 6). Am Wochenende (ca. 2026-09-13) folgt der reale Aufbau (3D-Druck, plane Ausrichtung), danach Kalibrierung/Messreihen-Fine-Tuning auf dem finalen Aufbau.
  - **ROS**: bleibt bei der bisherigen Abgrenzung aus `CLAUDE.md` — nur strukturelle Vorbereitung (Logik/I/O-Trennung, klare Datenschnittstelle für Pose/Trajektorie), kein echter ROS2-Code. Kein Änderungsbedarf, aktuelle Architektur erfüllt das bereits.
- Konsequenz: Der Rotationstest-Punkt aus dem zurückgestellten Tag 7 wird nicht separat als statische Stop-and-Shoot-Sequenz nachgeholt, sondern direkt im Rahmen der Live-VO-Umsetzung morgen mitgeprüft (siehe `CHECKLIST.md`, Tag 9).
- Offener Punkt / Rückspiegeln an Betreuer: Live-Erfassung weicht von der bisherigen `CLAUDE.md`-Begründung ab (Kamera steht während jeder Aufnahme still, kein Rolling-Shutter-Risiko *weil* Stop-and-Shoot). Je nachdem, wie "live" die Aufnahme morgen tatsächlich läuft (durchgehend fahrend vs. kurze Stopps mit Einzelaufnahmen), könnte das erneut ein Bewegungsunschärfe-Thema werden, auch bei Global-Shutter-Sensoren — beim Umbau morgen explizit prüfen. Wie schon beim Methodenwechsel 2026-09-04 vermerkt: diese zweite Scope-Abweichung vom ursprünglichen Projektbrief bei Gelegenheit mit Prof. Borchers-Tigasson rückspiegeln.

## 2026-09-14 — Neuer Kamera-Aufbau (feste Verschraubung), Neukalibrierung ohne mechanische Tilt-Korrektur

- Kontext: geplanter Mechanik-Umbau vom Wochenende (siehe 2026-09-10-Update) umgesetzt: beide Kameras jetzt fest auf einer gemeinsamen Metallschiene verschraubt statt wie zuvor nur genagelt (Foto `Aufbau2.HEIC`). Mechanisch deutlich stabilerer Aufbau als der alte, provisorische.
- Befund: rechtes Kameramodul sitzt sichtbar leicht schräg (Roll-Verkippung um die Blickachse) zur Schienenkante, linkes Modul sitzt sauber parallel.
- Alternativen: (a) vor der Neukalibrierung mechanisch nachjustieren, (b) Roll-Versatz unkorrigiert lassen und wie gehabt rechnerisch über `stereoRectify` ausgleichen.
- Entscheidung (User): (b), kein mechanischer Fix. Begründung: inhaltlich identisch zur bereits akzeptierten Roll-Verkippung des alten, nur genagelten Aufbaus (~2,25°, siehe 2026-09-02-Eintrag "Level-Check (Roll)") — ein rein optischer Rotationsversatz zwischen den beiden Kameras ist genau der Fall, für den `stereoRectify` da ist, kein Blocker. Passt zum etablierten Projektprinzip "erst funktionale Pipeline, dann Fine-Tuning" (siehe 2026-09-04).
- Konsequenz: Neukalibrierung ist trotzdem nötig — nicht wegen der Schräglage, sondern weil sich durch die neue feste Verschraubung Baseline und Relativ-Rotation der beiden Kameras gegenüber der Tag-5-Kalibrierung (altes, genageltes Setup) geändert haben dürften. Vor der Kalibrierung Baseline neu mit Maßband nachmessen (bisheriger Referenzwert 60mm / `MEASURED_BASELINE_M` in `scripts/run_calibration.py` stammt vom alten Aufbau, nicht blind übernehmen). Neues Kalibrierergebnis unter neuem Datum in `results/calibration/` ablegen, `2026-09-07_calibration.yaml` nicht überschreiben — bleibt als Vergleichspunkt stehen, um in der Arbeit den Effekt der festen Montage auf die Genauigkeit (Reprojection-Error, Baseline-Abweichung, Tiefenfehler) zu zeigen.

## 2026-09-14 (Update) — Neukalibrierung + Tiefenmessung auf dem neuen Mount: konstanter ~10,5%-Tiefenfehler, Ursache nicht Baseline/Board-Wölbung

- Kontext: Neukalibrierung auf dem neuen, festen Mount durchgeführt. Alte Kalibrierbilder (Tag 5) vorher nach `data/calibration_images_2026-09-07_old_mount/` verschoben (git-Historie erhalten), damit `data/calibration_images/` sauber für den neuen Aufbau bei Index 0 startet, statt beide Mounts im selben Manifest zu vermischen. Baseline frisch nachgemessen: **60mm** (auf mm genau, identisch zum alten Wert) — `MEASURED_BASELINE_M` in `scripts/run_calibration.py` unverändert korrekt.
- Kalibrierbilder: 12 Paare (nah/weit/links/rechts/geschrägt/oben im Bild). **Unterer Bildbereich fehlt** — die Board-Halterung ist an den Stuhllehnen befestigt, ein Abbau nur für Unten-Posen wurde als unverhältnismäßiger Aufwand eingeschätzt und nicht gemacht. Zwei fehlgeschlagene Aufnahmeversuche unterwegs (Board oben bzw. links im Bild abgeschnitten, jeweils Bild+Manifest-Zeile gelöscht und wiederholt, keine schlechten Daten im Datensatz).
- Ergebnis (`results/calibration/2026-09-14_calibration.yaml`): Intrinsics-Reprojection-Error 0,216px/0,225px (gut, vergleichbar mit 0,29px alt). Extrinsics-Reprojection-Error mit 7 Bildern noch 1,905px, nach den restlichen 5 Bildern (12 gesamt) auf **0,955px** verbessert — akzeptabel, aber immer noch höher als beim alten, 19-Bilder-Datensatz (0,707px). Berechnete Baseline **62,57mm** vs. 60mm Referenz (**+4,3%**, etwas mehr als die +2,3% beim alten Mount).
- Tiefenmessung (`scripts/measure_depth.py`, drei unabhängige Distanzen, nicht Teil der Kalibrierbilder):
  - 0,80m gemessen → 0,717m berechnet → **-83,4mm (-10,4%)**, Streuung 15,0mm über 42 Eckpunkte.
  - 1,30m gemessen → 1,162m berechnet → **-137,9mm (-10,6%)**, Streuung 6,3mm.
  - 1,60m gemessen → 1,423m berechnet → **-177,0mm (-11,1%)**, Streuung 6,0mm.
- Analyse: Der *relative* Fehler ist über eine Distanz-Verdopplung (0,8m→1,6m) auffällig konstant (-10,4% bis -11,1%, Spanne nur 0,7 Prozentpunkte) — deutlich enger beieinander als beim alten Mount (-6,2%/-7,5%, Spanne 1,3 Punkte über einen kleineren Distanzbereich). Ein derart distanzunabhängiger, konstanter relativer Fehler ist die typische Signatur eines reinen Skalierungsfehlers, nicht von zufälligem Rauschen (Maßband-Ablesefehler oder Board-Wölbung sollten stärker streuen).
- Kurze Ursachenprüfung (auf Wunsch User, keine tiefe Root-Cause-Analyse):
  - Einfacher Quadratgrößen-Skalierungsfehler ausgeschlossen: ein solcher Fehler würde Baseline- und Tiefenfehler in dieselbe Richtung verschieben. Hier stehen sie sich entgegen (Baseline +4,3% zu groß, Tiefe ~10,5% zu klein) — dasselbe Vorzeichen-Rätsel wie schon bei Tag 5 (dort +2,3% vs. -6/-7,5%), diesmal aber deutlich größer und konsistenter.
  - Board-Wölbung (Tag-5-Verdacht) passt schlechter als Erklärung als beim ersten Mal: die geringe Streuung pro Messung (6-15mm über 42 Punkten) UND die enge Konsistenz des relativen Fehlers über drei Distanzen sprechen eher gegen eine unregelmäßige physische Verformung.
  - Wahrscheinlichste Erklärung: unzureichende Posen-Vielfalt in den 12 Kalibrierbildern (kein unterer Bildbereich, insgesamt weniger Bilder als der alte 19-Bilder-Datensatz) — kann einen systematischen, distanzunabhängigen Bias in der gemeinsamen Fokuslänge-/Baseline-Schätzung erzeugen, der sich als konstanter prozentualer Tiefenfehler unabhängig von der Objektdistanz äußert. Nicht abschließend verifiziert (dafür müsste man mit einem vollständigeren Datensatz neu rechnen und vergleichen).
- Entscheidung (User): Für den aktuellen Stand akzeptiert, keine weitere Root-Cause-Analyse jetzt (z.B. kein Umbau der Board-Halterung nur für bessere Kalibrierbilder). Passt zum etablierten Projektprinzip "erst funktionale Pipeline, dann Fine-Tuning". Root-Cause-Klärung (vollständigere Kalibrierbild-Abdeckung, ggf. mit einer vom Stuhl unabhängigen Board-Halterung) bleibt offen für die Fine-Tuning-Phase.
- Für die Arbeit: guter Diskussionspunkt für die Limitations-Sektion — zeigt, dass ein niedriger Reprojection-Error (0,955px, auf den ersten Blick unauffällig) nicht automatisch geringe Tiefenfehler garantiert, wenn die zugrunde liegende Posen-Abdeckung der Kalibrierbilder lückenhaft ist. Der Vorzeichen-Widerspruch zwischen Baseline- und Tiefenfehler (hier wie schon bei Tag 5) ist ebenfalls ein guter Beleg dafür, dass ein einzelner Kennwert (z.B. nur der Reprojection-Error) nicht ausreicht, um die tatsächliche Messgenauigkeit einzuschätzen.

## 2026-09-15 — Ground-Truth-Format: pro Sequenz statt globaler `reference_points.yaml`

- Kontext: Vor Tag 11 (zweite Translationssequenz mit neuem Mount) musste die seit Tag 7 offene Design-Frage geklärt werden: `data/reference_points.yaml` war eine einzelne, positionsbasierte Punktliste (Frame-Index ↔ Listenposition), die nur für die eine Tag-6-Sequenz ausgelegt war. Eine zweite Sequenz mit anderer Frame-Zahl/Route hätte entweder die Tag-6-Punkte überschrieben oder beide Sequenzen ununterscheidbar in derselben Liste vermischt.
- Alternativen: (a) verschachteltes Format in einer zentralen Datei (`sequences: {name: {points: {...}}}`); (b) Ground-Truth pro Sequenz direkt neben den Bildern ablegen (`data/vo_sequences/<name>/ground_truth.yaml`), `reference_points.yaml` nur noch für die globale Achsenkonventions-Doku.
- Entscheidung: (b), wie in Tag 7 skizziert. Begründung: Ground-Truth liegt damit bei den Rohdaten, zu denen sie gehört (analog zu `manifest.csv` je Sequenz), kein Risiko mehr, dass Punkte verschiedener Sequenzen verwechselt werden, kein zusätzliches Verschachtelungs-Format nötig.
- Umsetzung: Tag-6-Punkte (`start`, `wp_020cm`…`wp_120cm`) von `data/reference_points.yaml` nach `data/vo_sequences/2026-09-08_tisch_translation/ground_truth.yaml` umgezogen. `reference_points.yaml` enthält nur noch die Achsenkonventions-Doku, `points: {}`. `scripts/run_vo_sequence.py` sucht die Ground-Truth jetzt standardmäßig unter `<sequence-dir>/ground_truth.yaml`; `scripts/plot_trajectory_map.py` leitet den Sequenz-Ordner aus dem `sequence_dir`-Feld der `trajectory.yaml` ab. `--reference-points` bleibt in beiden Skripten als expliziter Override erhalten. Kein Eingriff in `src/` nötig (die VO-Pipeline selbst liest die Datei ohnehin nicht, Startpose-Anker ist Code-intern immer `[0,0,0]` bei Frame 0). Verifiziert: alle 60 Tests weiterhin grün, `run_vo_sequence.py` + `plot_trajectory_map.py` gegen die Tag-6-Sequenz probeweise gelaufen, Ground-Truth-Vergleich liefert dieselben Werte wie vorher.

## 2026-09-15 (Update) — Fehlerbetrachtung: konstanter ~10,5%-Tiefenfehler mathematisch in Offset- und Skalierungsanteil zerlegt

- Kontext: Auf Basis der drei Tiefenmessungen vom 2026-09-14 (0,80m/1,30m/1,60m, siehe Eintrag oben) drei mögliche Fehlerquellen diskutiert (User): (1) Maßband-Ungenauigkeit bei der Baseline-Messung (60mm ± 2-3mm), (2) Referenzpunkt-Unsicherheit bei der Distanzmessung Kamera→Brett (Zollstock-Nullpunkt an der Kameragehäuse-Spitze statt am tatsächlichen optischen Zentrum, geschätzter möglicher Fehler 5-7cm), (3) generelle Kalibrier-Ungenauigkeit durch die bereits dokumentierte lückenhafte Posen-Abdeckung (siehe Eintrag oben).
- **Prüfung Hypothese (1) am Code**: `MEASURED_BASELINE_M` (`scripts/run_calibration.py`) wird ausschließlich für den Print-Vergleichswert genutzt (`calibrate_extrinsics()`, `src/calibration/extrinsics.py`), nicht für die Tiefenberechnung — die tatsächlich verwendete Baseline stammt vollständig aus `stereoCalibrate()`, verankert an der Schachbrett-Quadratgröße (24mm). Die Maßband-Baseline-Unsicherheit (2-3mm/60mm ≈ 3,3-5%) erklärt damit plausibel die beobachtete **+4,3%-Baseline-Abweichung** im Plausibilitätscheck (Tag 10), hat aber **keinen Einfluss** auf die Tiefenmessung selbst.
- **Trennung Hypothese (2) vs. (3) per linearer Regression**: Ein reiner Referenzpunkt-Offset erzeugt einen distanzunabhängigen, additiven Fehler (`Fehler(D) = a`, relativ mit wachsender Distanz schrumpfend); ein Skalierungsfehler (z.B. aus Brennweiten-/Baseline-Bias) erzeugt einen zu D proportionalen Fehler (`Fehler(D) = k·D`, relativ konstant). Ausgleichsrechnung `Fehler(D) = a + k·D` mit den drei Messpunkten (−83,4mm/−137,9mm/−177,0mm bei 0,80/1,30/1,60m):
  - **a ≈ +10,5mm** (Offset-Anteil)
  - **k ≈ −11,6%** (Skalierungsanteil)
  - Residuen (Modell vs. Ist): 1,0mm / 2,6mm / 1,6mm — im Bereich der ohnehin dokumentierten Punktwolken-Streuung (6-15mm), Modell passt gut.
- **Ergebnis**: Bei 1,6m trägt der Skalierungsanteil ca. −186mm bei, der Offset-Anteil nur +10,5mm — der Fehler ist zu **~90-95% ein Skalierungsfehler**, der von User vermutete Referenzpunkt-Versatz ist real, aber mit **~1cm statt geschätzter 5-7cm** ein kleiner Nebeneffekt, nicht der Haupttreiber. Bestätigt Hypothese (3) als dominante Ursache.
- **Zusatzbefund**: Baseline-Check (+4,3%, Kalibrierung "zu groß") und Tiefenfehler-Skalierungsanteil (−11,6%, Kalibrierung "zu klein") haben entgegengesetzte Vorzeichen — ein einfacher globaler "Schachbrett-Maßstab falsch interpretiert"-Fehler würde beide Werte in dieselbe Richtung verschieben (da beide auf derselben, aus der Quadratgröße abgeleiteten Baseline beruhen) und scheidet damit als Erklärung aus (bereits in obigem Eintrag vermutet, hier zusätzlich mathematisch untermauert). Wahrscheinlichste Erklärung bleibt eine durch lückenhafte Posen-/Distanz-Abdeckung schlecht konditionierte Entkopplung von Brennweite und Tiefenskala in der Kalibrierung (Reprojection-Error auf den Kalibrierbildern bleibt niedrig, während die absolute Tiefenskala für neue, unabhängige Testbilder trotzdem verzerrt sein kann) — klassisches Degenerationsproblem bei zu geringer Distanz-Varianz in den Kalibrieraufnahmen.
- **Einschränkung**: nur 3 Datenpunkte für 2 Parameter (a, k) — nur 1 Freiheitsgrad, Trennung plausibel und mit kleinen Residuen, aber statistisch nicht robust abgesichert. Mehr Distanzmessungen (5+, auch näher als 0,80m) würden die Trennung für den Bericht belastbarer machen.
- **Konsequenz / priorisierte Maßnahmen für die spätere Fine-Tuning-Phase** (jetzt nicht umgesetzt, passt zum Projektprinzip "erst funktionale Pipeline, dann Fine-Tuning"):
  1. Kalibrieraufnahmen mit größerer Distanz-Varianz (nah UND fern) — wahrscheinlichster Hebel gegen den dominanten Skalierungsfehler
  2. Unteren Bildbereich in den Kalibrierbildern abdecken (aktuell komplett fehlend, Board hängt an der Stuhllehne)
  3. Mehr Kalibrierbilder insgesamt (aktuell 12, alter Datensatz mit 19 hatte kleineren Fehler)
  4. Feste, plane Board-Montage statt Karton+Stuhllehne (Wölbungsrisiko, bisher nicht Haupttreiber, aber Nebeneffekt)
  5. Für künftige Tiefenmessungen: fester, klar definierter/markierter Referenzpunkt statt "vorderste Gehäusespitze" (reduziert den kleinen Offset-Anteil weiter, nicht der Haupthebel)
  - Explizit NICHT priorisiert: eine "bessere" Schachbrett-Druckqualität — das Problem liegt an der Posen-/Distanz-Vielfalt der Aufnahmen, nicht am Muster selbst.
- Für die Arbeit: gutes Beispiel für eine nachvollziehbare, quantitative Fehlerzerlegung (Regression aus wenigen Messpunkten) statt reiner Spekulation über Fehlerursachen — inkl. ehrlicher Angabe der schwachen statistischen Aussagekraft (n=3) als Grenze der Methode.

## 2026-09-15 (Update 2) — Neukalibrierung mit mehr Posen-Varianz: Baseline-Fehler fast behoben, Tiefen-Skalierungsfehler nur teilweise

- Kontext: Auf Basis der Fehlerbetrachtung oben (Skalierungsfehler als Haupttreiber, vermutlich durch lückenhafte Posen-/Distanz-Abdeckung der 12 Kalibrierbilder) wurde die Kalibrierung mit deutlich mehr Bildern wiederholt. Schachbrett dafür freihändig gehalten statt am festen Stuhllehnen-Mount — ermöglichte erstmals auch Nahbereich (~0,3-0,5m) und unteren Bildbereich, beide zuvor als nicht abgedeckt dokumentiert.
- Aufnahme-Ablauf: zunächst automatisierter Burst-Versuch (`scripts/capture_calibration_burst.py`, alle 10s automatisch ausgelöst) — Live-Feedback über den Chat war technisch nicht möglich (Python puffert `print()`-Ausgaben beim Schreiben in eine Datei/Pipe, dadurch kam nichts in Echtzeit an). Von den 14 unbeaufsichtigt aufgenommenen Bildern hatten nur 5 (Index 12-16) in beiden Haelften erkannte Ecken (Board vermutlich oft ausserhalb des Bildausschnitts, da Timing unklar) — die 9 nicht erkannten wurden geloescht, die 5 brauchbaren mit ehrlicher Notiz ("Pose nicht dokumentiert") behalten. Danach auf manuellen Ablauf umgestellt: User sagt "go", Aufnahme wird einzeln ausgelöst (`capture_one_calibration_image.py`), sofortiges Ecken-Erkennungs-Feedback im Chat. Dabei zwei diagnostizierte Fehlversuche: Board einmal komplett ausserhalb des Bildausschnitts (ueber Kopfhoehe gehalten), einmal nur klein am Bildrand abgelegt statt aktiv gehalten -- beide durch Betrachten des jeweiligen Rohbilds erkannt und korrigiert.
- Ergebnis: 33 Bildpaare im Manifest (12 alt + 5 Burst + 16 manuell, davon 5 manuelle ohne erkanntes Muster), **28 fuer die Kalibrierung nutzbar** (`run_calibration.py` ueberspringt den Rest automatisch). Neues Ergebnis: `results/calibration/2026-09-15_calibration.yaml`.
- **Vergleich alt (12 Bilder, 2026-09-14) vs. neu (28 Bilder, 2026-09-15)**:
  - Intrinsics-Reprojection-Error: 0,216/0,225px → **0,182/0,184px**
  - Extrinsics-Reprojection-Error: 0,955px → **0,407px** (weniger als halb so gross)
  - Baseline: 62,57mm (+4,3% vs. 60mm Massband) → **59,70mm (−0,5%)** — praktisch am Referenzwert
- **Tiefenmessung wiederholt** (dieselben drei Distanzen wie Tag 10, `scripts/measure_depth.py`):
  - 0,80m → 0,744m → **−56,1mm (−7,0%)**, Streuung 4,4mm (vorher −83,4mm/−10,4%)
  - 1,30m → 1,202m → **−98,2mm (−7,6%)**, Streuung 4,3mm (vorher −137,9mm/−10,6%)
  - 1,60m → 1,470m → **−130,1mm (−8,1%)**, Streuung 5,7mm (vorher −177,0mm/−11,1%)
  - Fehler um ca. 25-33% kleiner geworden, aber nicht behoben.
- **Aktualisierte Offset/Skalierungs-Zerlegung** (gleiche lineare Ausgleichsrechnung `Fehler(D) = a + k·D` wie im Eintrag oben): **a ≈ +18,3mm** (Offset-Anteil, vorher +10,5mm), **k ≈ −9,2%** (Skalierungsanteil, vorher −11,6%). Residuen 1,0-2,7mm, Modell passt weiterhin gut.
- **Interpretation**: Die Baseline-Übereinstimmung ist mit der neuen Kalibrierung fast perfekt (+4,3% → −0,5%), der Tiefen-Skalierungsfehler aber nur um ~21% kleiner geworden (−11,6% → −9,2%), nicht behoben. Zeigt: eine gute Baseline-Schätzung (aus `stereoCalibrate`) ist notwendig, aber nicht hinreichend für eine genaue absolute Tiefe — vermutlich tragen Brennweite/Verzeichnung oder weitere, mit dieser Bildmenge noch nicht behobene Kalibrier-Feinheiten zum verbleibenden Skalierungsfehler bei. Der Offset-Anteil (~1-2cm) bleibt über beide Kalibrierungen hinweg in ähnlicher Größenordnung, wie erwartet, da er kalibrierungsunabhängig ist (Referenzpunkt-Unsicherheit bei der Zollstock-Messung, nicht durch bessere Kalibrierbilder behebbar).
- Entscheidung (User): Ergebnis für den aktuellen Stand akzeptiert, keine weitere Kalibrier-Iteration jetzt (z.B. noch mehr Bilder oder Distortion-Modell pruefen) -- passt zum etablierten Projektprinzip "erst funktionale Pipeline, dann Fine-Tuning". Verbleibender ~7-8%-Tiefenfehler bleibt dokumentierte Einschränkung fuer die Fine-Tuning-Phase.
- Für die Arbeit: gutes Vorher-Nachher-Beispiel, dass die vermutete Ursache (Posen-/Distanz-Abdeckung) tatsächlich einen messbaren Anteil des Fehlers erklärt (quantifiziert über dieselbe Offset/Skalierungs-Regression), aber nicht den ganzen -- unterstreicht den Wert, Fehler in Komponenten zu zerlegen statt nur eine Gesamt-Kennzahl zu berichten.

## 2026-09-15 (Update 3) — Zweite VO-Sequenz (neuer Mount, verbesserte Markierungen): Ausreißer behoben, aber systematischer Drift größer

- Kontext: Zweite Translations-Testsequenz (Tag-11-Ziel), direkt vergleichbar mit der Tag-6-Sequenz (`data/vo_sequences/2026-09-08_tisch_translation/`): reine Lateralbewegung, 20cm-Schritte, 7 Bildpaare (0-120cm). Diesmal mit dem neuen, fest verschraubten Mount, verbesserten Tisch-Markierungen für präzisere Positionierung, und einem zusätzlichen texturreichen Objekt im Bild -- gezielt gegen den bei Tag 6 diagnostizierten Merkmalsschwund in der Ferne (Kommode/Vorhang wanderte aus dem Bild). Neue Sequenz: `data/vo_sequences/2026-09-15_tisch_translation/`, ausgewertet mit `run_vo_sequence.py` gegen die neue Kalibrierung (`2026-09-15_calibration.yaml`, siehe Update 2 oben).
- **Vergleich (3D-Abstand geschätzte Position vs. Massband-Ground-Truth, identische Metrik in beiden Sequenzen)**:

  | Frame/Distanz | Tag 6 (alt, 12.09./2026-09-07-Kalibrierung) | Tag 11 (neu, 2026-09-15-Kalibrierung) |
  |---|---|---|
  | 20cm | 5,5cm | 9,6cm |
  | 40cm | 1,9cm | 8,8cm |
  | 60cm | 7,5cm | 17,5cm |
  | 80cm | 11,1cm | 26,7cm |
  | 100cm | 19,4cm | 36,8cm |
  | 120cm | **569cm (Ausreißer)** | 34,1cm |

- **Positiver Befund**: Der bei Tag 6 beobachtete katastrophale Ausreißer bei 120cm (Merkmalszahl bricht ein, RANSAC unterbestimmt) tritt in der neuen Sequenz nicht mehr auf -- die Trajektorie bleibt über die gesamte Strecke stabil (siehe `results/measurements/2026-09-15_vo_sequence_test/trajectory_map.png`). Zusätzliches Objekt + stabilerer Mount haben das ursprüngliche Problem behoben.
- **Negativer Befund**: Der Drift pro Schritt ist in der neuen Sequenz durchgehend etwa doppelt so groß wie bei Tag 6 (Frames 1-5, Tag 6 ohne Ausreißer: Mittel ~9,1cm; Tag 11: Mittel ~19,9cm). Die geschätzte Trajektorie bleibt systematisch hinter der Ground Truth zurück (bei 120cm geschätzt nur 88,2cm statt 120cm, ein Untertreiben um durchgehend ~20-48% je Frame, meist im Bereich 25-35%).
- **Mögliche Teilursache, nicht abschließend geklärt**: Die VO baut auf denselben triangulierten Stereo-3D-Punkten auf, für die weiterhin ein ~7-8%-Tiefen-Skalierungsfehler dokumentiert ist (Update 2 oben) -- ein systematisch zu kleiner Tiefenwert würde plausibel zu einer systematisch zu kleinen geschätzten Translation führen. Die Größenordnung passt aber nicht vollständig: 25-35% Untertreiben ist deutlich mehr, als ein 7-8%-Tiefenfehler alleine erklären würde. Weitere mögliche Beitragende (nicht einzeln quantifiziert): 2D-Feature-Lokalisierungsrauschen, RANSAC-Inlier-Auswahl-Effekte über mehrere verkettete Frame-Übergänge, oder eine nicht perfekt orientierungskonstante Kamera-Führung trotz Tisch-Markierungen.
- Entscheidung (User): Ergebnis dokumentiert, keine sofortige Ursachenklärung -- passt zum Projektprinzip "erst funktionale Pipeline, dann Fine-Tuning". Für die Arbeit ein guter Diskussionspunkt: zwei unterschiedliche Fehlerarten (katastrophaler Ausreißer durch Merkmalsschwund vs. systematischer Drift durch Tiefenskalierung) mit unterschiedlichen, teils gegenläufigen Ursachen und Gegenmaßnahmen -- eine einzelne Verbesserung (mehr Merkmale) behebt nicht automatisch die andere (Tiefengenauigkeit).
- Ergebnisse abgelegt: `results/measurements/2026-09-15_vo_sequence_test/trajectory.yaml` + `trajectory_map.png`.

## 2026-09-15 (Update 4) — Projektstand-Einordnung + Optimierungs-Loop-Idee zurückgestellt

- Kontext: Nach dem gemischten Ergebnis der zweiten VO-Sequenz (Update 3) kam die Frage auf, ob das Projekt nach Rotationstest + Live-VO (geplant für Tag 12) im Wesentlichen fertig sei ("nur noch Optimierung"), und ob eine bekannte, gefilmte Sequenz mit bekanntem Weg/Rotation als Grundlage für einen automatisierten Optimierungs-Loop (Claude durchsucht VO-interne Parameter, wertet die Sequenz wiederholt aus) dienen könnte.
- **Projektstand-Einordnung**: Rotation + Live-VO würden Phase 2 (Lokalisierungsalgorithmus) funktional abschließen, aber Phase 3 (Validierung: systematische Messreihen, ATE/RPE-Metriken) ist weiterhin größtenteils offen (`src/evaluation/` bisher nur `__init__.py`, bisher nur 2 kurze Sequenzen à 7 Frames, kein Rotationsfehler-Maß) -- ebenso die eigentliche schriftliche Arbeit (Projektziel ist laut `CLAUDE.md` "schriftliche Arbeit + Code", bisher nur Rohmaterial in `docs/decisions.md`). Einschätzung "fertig bis auf Optimierung" korrigiert.
- **Optimierungs-Loop-Idee**: technisch machbar, aber zwei konkrete Einwände statt pauschaler Vorsicht:
  1. Überanpassung: Parameter gegen genau eine Sequenz zu optimieren riskiert, auf Zufälligkeiten dieser einen Szene/Beleuchtung/Bewegung zu optimieren statt auf etwas generell Besseres -- ohne zweite, unabhängige Sequenz zur Validierung nicht aussagekräftig.
  2. Ansatzpunkt fraglich: der bisher dominante Fehler (Tiefen-Skalierungsfehler aus der Kalibrierung, ~7-8%, siehe Update 2) wird durch VO-interne Parameter (ORB-Feature-Anzahl, RANSAC-Schwellwert, Matching-Ratio) vermutlich nicht behoben -- diese beeinflussen die Punktauswahl/Robustheit des Matchings, nicht die zugrunde liegenden Tiefenwerte aus der Kalibrierung. Eine automatisierte Suche könnte den Trajektorienfehler durch Zufall (andere Punktauswahl/Ausreißer) verbessern, ohne die eigentliche Ursache zu adressieren.
  3. Passt schlecht zum etablierten Projektprinzip "Nachvollziehbarkeit" (`CLAUDE.md`, explizit zur Vermeidung von "Vibe-Coding"-Risiko): eine Blackbox-Optimierungsschleife ohne dokumentierte Begründung, warum bestimmte Parameterwerte gewählt wurden, passt schlechter zum bisherigen Stil (kleine, begründete Schritte in diesem Log) als eine bewusste Sensitivitätsprüfung.
- Entscheidung (User): Idee zurückgestellt, nicht verworfen. Vorgemerkt für nach Abschluss von Phase 3, dann als begründete Sensitivitätsprüfung (wenige bewusst gewählte Parameterwerte, nicht automatisiert durchsucht) über mindestens zwei unabhängige Sequenzen statt als automatisierter Optimierungs-Loop gegen eine einzelne Aufnahme. Siehe `CHECKLIST.md`, Abschnitt "Vorgemerkt (nach Phase 3)".
- Tag 12 (2026-09-16) bleibt wie vorgeschlagen: zuerst Rotationstest mit echten Daten (kein neuer Code nötig, Kabsch-Algorithmus unterstützt bereits volle Rotation+Translation, siehe `tests/test_pose_estimation.py::test_estimate_relative_pose_recovers_known_rotation_and_translation`, auf synthetischen Daten mit <0,1° Fehler verifiziert, aber nie an echten Kameradaten getestet), danach Umstellung auf Live-VO.

## 2026-09-16 — `src/evaluation/` (ATE/RPE) implementiert, kein Pi-Zugriff verfügbar

- Kontext: User ohne Pi-Zugriff an diesem Tag, Tag-12-Punkte (Rotationstest, Live-VO-Latenz-Benchmark) brauchen beide die Kamera und wurden auf morgen verschoben. Stattdessen den in Update 4 (2026-09-15) identifizierten größten nicht-Hardware-Blocker für Phase 3 angegangen: `src/evaluation/` war bis dahin nur `__init__.py`.
- Implementiert: `src/evaluation/metrics.py` mit `absolute_trajectory_error()` (ATE), `relative_pose_error()` (RPE, Translation), `rotation_error_deg()` (Rotationswinkel-Fehler, Baustein für Tag 12). 11 neue Tests in `tests/test_metrics.py` (bekannte Konstanten-Offsets, bekannte Skalierungsfehler, bekannte 90°-Rotation), alle 71 Tests im Repo weiterhin grün.
- **Design-Entscheidung: kein Trajektorien-Alignment vor ATE/RPE.** Im TUM-RGBD-Benchmark üblich ist ein Umeyama-/Horn-Alignment (Rotation+Translation+ggf. Skalierung) zwischen geschätzter und Ground-Truth-Trajektorie vor der Fehlerberechnung, um einen beliebigen globalen Versatz/Rotationsoffset auszugleichen, der bei monokularen/nicht verankerten SLAM-Systemen typischerweise vorliegt. Hier explizit weggelassen: die VO-Trajektorie ist an einem vermessenen Startpunkt verankert und nutzt dieselbe Achsenkonvention wie die Ground-Truth-Wegpunkte (siehe `ground_truth.yaml`-Header) -- beide liegen bereits im selben Koordinatensystem. Ein zusätzliches Alignment würde den real vorhandenen Drift (das eigentliche Messziel) künstlich kleinrechnen statt ihn zu zeigen. Passt auch zur bisherigen manuellen Auswertungsmethode in diesem Log (direkter 3D-Abstand, kein Fitting).
- `scripts/evaluate_trajectory.py` (analog zu `plot_trajectory_map.py`) angelegt, gegen beide vorhandenen echten Sequenzen gelaufen:

  | Metrik | Tag 6 (2026-09-08) | Tag 11 (2026-09-15) |
  |---|---|---|
  | ATE RMSE | 2,15m (durch 120cm-Ausreißer dominiert) | 0,23m |
  | ATE Mean | 0,88m | 0,19m |
  | RPE RMSE (delta=1) | 2,32m (Ausreißer) | 0,08m |
  | RPE Mean (delta=1) | 1,00m (Ausreißer) | 0,075m |

  Bestätigt quantitativ, was in Update 3 (2026-09-15) bereits qualitativ beschrieben war: Tag 6 hat den bekannten Merkmalsschwund-Ausreißer bei 120cm (dominiert RMSE/Mean, ohne ihn wäre Tag 6 deutlich niedriger als Tag 11), Tag 11 hat keinen Ausreißer mehr, aber einen konsistenten RPE-Fehler von ~5-10cm pro 20cm-Schritt. Reports abgelegt: `results/measurements/2026-09-08_vo_sequence_test/evaluation.yaml`, `results/measurements/2026-09-15_vo_sequence_test/evaluation.yaml`.
- Noch offen für spätere Iterationen (nicht heute umgesetzt): `rotation_error_deg()` ist noch nicht in `relative_pose_error()` integriert, weil `trajectory.yaml` aktuell nur Positionen speichert, keine vollen Posen (Rotation geht bei der Serialisierung in `run_vo_sequence.py` verloren). Muss ergänzt werden, sobald der Tag-12-Rotationstest eine RPE-Rotationskomponente braucht.

## 2026-09-16 (Teil 2) — Live-VO-Umstellung (Code) vorbereitet, RANSAC-Nichtdeterminismus gefunden

- Kontext: weiterhin kein Pi-Zugriff. Zweiter nicht-Hardware-Punkt aus der Tag-12-Vorbereitung angegangen: die für Live-VO nötige Umstellung von "kompletter Bild-Batch rein, fertige Trajektorie raus" auf "ein neuer Frame rein, sofort neue Pose raus" (`CHECKLIST.md`, Tag 9/11/12) lässt sich komplett am Code entwickeln und gegen die vorhandenen echten Sequenzen verifizieren -- nur der eigentliche Kamera-Latenz-Benchmark braucht morgen den Pi.
- **`src/localization/vo_pipeline.py` umgebaut**: neue Funktionen `init_vo_step()` (Zustand für Frame 0) und `step_vo_pipeline()` (verarbeitet einen neuen Frame gegen den Zustand des vorherigen) sind jetzt die Kernprimitive -- genau das, was eine Live-Aufnahmeschleife morgen pro aufgenommenem Frame aufrufen wird. `run_vo_pipeline()` (die bisherige Batch-Funktion) ist jetzt nur noch eine dünne Schleife über diese Primitive, keine eigene Logik mehr -- Batch- und Live-Verarbeitung können dadurch nicht mehr auseinanderlaufen. Bewusst weiterhin keine Klassen (Zustand wird explizit durch den Rückgabewert gereicht, wie bereits bei `src/capture/sequence.py`s `next_free_index()`) -- konsistent mit dem rein funktionalen Stil im restlichen Codebase.
- 4 neue Tests in `tests/test_vo_pipeline.py`, u.a. ein Regressionstest, der beweist, dass Batch- und Schritt-für-Schritt-Verarbeitung bei gleichem Seed exakt dieselbe Trajektorie liefern. `scripts/run_vo_sequence.py` auf dieselbe Frame-für-Frame-Schleife umgestellt (Pose wird direkt nach jedem Frame ausgegeben statt erst am Ende) -- Bildquelle bleibt die Platte, aber die Verarbeitungsschleife ist jetzt identisch zu der, die die Live-Aufnahme morgen nutzen wird. Alle 75 Tests grün, keine Regression.
- **Nebenbefund beim Verifizieren gegen die Tag-6-Sequenz**: `run_vo_sequence.py` hat `run_vo_pipeline()` nie mit einem festen RANSAC-Seed aufgerufen (Default `seed=None`). Bei Frame 6 (dem bekannten Merkmalsschwund-Fall mit nur ~4 RANSAC-Inliern, siehe 2026-09-08) schwankte der Positionsfehler zwischen drei Läufen derselben Sequenz zwischen 26cm, 108cm und 195cm -- reiner RANSAC-Sampling-Zufall, kein Refactoring-Bug (verifiziert: mit explizitem Seed lieferten alte Batch-Logik und neue Schritt-für-Schritt-Logik bitidentische Ergebnisse). Widerspricht dem Nachvollziehbarkeits-Prinzip (`CLAUDE.md`) -- ein einzelner historisch dokumentierter Fehlerwert (z.B. die 569cm bei Frame 6 im Update-3-Eintrag oben) war nie exakt reproduzierbar, nur eine von vielen möglichen Zufallsziehungen.
- **Fix**: `run_vo_sequence.py` hat jetzt einen `--seed`-Parameter (Default `0`), der bis in `step_vo_pipeline()` durchgereicht wird, plus wird der verwendete Seed jetzt mit in `trajectory.yaml` gespeichert. Ergebnisse sind damit ab sofort reproduzierbar (verifiziert: 3 identische Läufe mit Seed 0). Historische Werte in diesem Log bleiben als "eine beobachtete Realisierung bei ungesetztem Seed" stehen, nicht als exakt nachstellbare Referenzwerte -- für die schriftliche Arbeit relevant: die dokumentierten Tag-6/Tag-11-Vergleiche sollten entsprechend eingeordnet werden (Größenordnung/Tendenz aussagekräftig, exakte Zentimeterwerte bei merkmalsarmen Frames nicht).
- Nicht heute umgesetzt: die eigentliche Live-Aufnahmeschleife (Kamera-Trigger statt Datei-Laden pro Frame, z.B. `scripts/run_vo_live.py`) -- das ist reine I/O-Verdrahtung um dieselben jetzt fertigen Primitive, aber ungetestet ohne Kamera sinnlos zu schreiben. Für Tag 12/17: `camera.capture_frame()` + `camera.split_stereo_frame()` pro Schleifendurchlauf statt `load_rectified()`, plus der Latenz-Benchmark davor (siehe `docs/decisions.md`, 2026-09-08).
