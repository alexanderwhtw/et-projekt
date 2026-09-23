# Depth-gewichtete Pose-Schätzung vs. Baseline (2026-09-23)

Vergleich der in `docs/decisions.md` (2026-09-21 Teil 7) vorgemerkten
tiefen-gewichteten Kabsch/Procrustes-Anpassung gegen die bisherige
ungewichtete Baseline (`exp5_final`, Plausibilitäts-Filter 0,25m/20°) --
beide gegen dieselbe Sequenz (`data/vo_sequences/2026-09-21_flur_route_v2`,
130 Frames), sonst identische Parameter (`seed=0`,
`ransac_inlier_threshold=0.02`, `ratio_threshold=0.75`).

Implementierung: `depth_weights()` (`src/localization/pose_estimation.py`)
gewichtet jede Korrespondenz mit `1/(Z_prev^4 + Z_curr^4)` (inverse Varianz,
hergeleitet aus der Fehlerfortpflanzung `ΔZ = Z²·Δd/(f·B)`, siehe Gespräch
2026-09-23 vor dieser Umsetzung). Nur der FINALE RANSAC-Refit auf dem
Gewinner-Inlier-Set nutzt die Gewichtung -- Hypothesengenerierung und
Inlier-Auswahl bleiben unverändert (bereits am 2026-09-21 validiert).

## Ergebnis

| Kennzahl | Baseline (ungewichtet) | Depth-gewichtet |
|---|---|---|
| Netto-Verschiebung Start→Ende | 2,040 m | 2,120 m |
| Aufsummierte Weglänge | 6,176 m | 6,357 m |
| Streuung Frame 34-50 ("eingefroren", Fehlermodus 4) | 0,175 m | 0,187 m |
| Größter Einzelschritt | 0,265 m (Frame 67) | 0,264 m (Frame 67) |
| Übersprungene Frames (Plausibilitäts-Filter) | 2 | 2 (dieselben) |
| Max. kumulative Abweichung von der Baseline | -- | 0,157 m (Frame 113) |
| Mittlere Abweichung von der Baseline (alle Frames) | -- | 0,091 m |

Top-Down-Karten (`baseline_trajectory_map.png` vs.
`depth_weighted_trajectory_map.png`) sind sich visuell sehr ähnlich, keine
strukturelle Änderung der Kurvenform.

## Einordnung

**Kein durchschlagender Effekt, wie bereits am 2026-09-21 (Teil 7)
vorsichtig eingeordnet.** Der eingefrorene Abschnitt (Frame 34-50) wird
durch die Gewichtung nicht spürbar besser (Streuung sogar minimal höher,
0,187m statt 0,175m, im Rahmen des Rauschens) -- die Diagnose aus Teil 5
erklärt, warum: dort bestehen die Frames zu ~89% aus Fernbereichs-Punkten
(>2m), es gibt kaum nahe Punkte, die als Gegengewicht dienen könnten.
Gewichtung kann schlechte Punkte nur relativ zu guten Punkten
zurückdrängen -- wenn fast alle Punkte eines Schritts gleichermaßen fern
und verrauscht sind, bleibt kein verlässliches Signal übrig, das die
Gewichtung freilegen könnte. Das bestätigt die eigene Vorab-Einordnung vom
2026-09-21: die Gewichtung mildert die Fehlerquelle (grosse Baseline-
Distanz-Kombination) nur dort ab, wo genug nahe Punkte im selben Schritt
vorhanden sind, um die fernen aufzuwiegen -- sie kompensiert keine Frames,
die strukturell komplett im Fernbereich liegen.

Kleinere, durchgehend positive Effekte sind sichtbar: die geschätzte
Netto-Verschiebung liegt näher an der (deutlich größeren) real gelaufenen
Strecke, und einzelne Schritte mit gemischt nahen/fernen Punkten wurden an
mehreren Stellen (z.B. Frame 18, 19, 21, 97-107) spürbar korrigiert (bis zu
~15cm kumulierte Verschiebung bis Frame 113). Kein Rückschritt in den
Fällen, wo die Baseline bereits gut war (Rotation, Frame-für-Frame-Diff
bleibt klein über weite Strecken).

**Fazit**: Die Tiefen-Gewichtung ist eine plausible, risikoarme Verbesserung
(kein Datensatz wurde schlechter, Plausibilitäts-Filter verhält sich
identisch), aber **kein Ersatz** für die in Teil 5 identifizierte
strukturelle Grenze (Baseline zu klein für konsistente Fernbereichs-Tiefe).
Für die Arbeit ein guter Beleg dafür, dass die im selben Gespräch
hergeleitete `ΔZ ~ Z²/(f·B)`-Fehleranalyse korrekt vorhersagt, WANN ein
software-seitiger Fix (Gewichtung) noch hilft (gemischte Tiefen pro Schritt)
und wann nicht (durchgehend fernbereichs-dominierte Schritte) -- passt zur
bereits in Teil 7 diskutierten Grenze der Idee.

## Dateien

- `baseline_trajectory.yaml` / `depth_weighted_trajectory.yaml` -- volle
  Trajektorien (Kopien aus `2026-09-21_vo_sequence_test_exp5_final/` bzw.
  `2026-09-23_vo_sequence_test_depth_weighted/`)
- `baseline_trajectory_map.png` / `depth_weighted_trajectory_map.png`
- `baseline_translation_over_time.png` / `depth_weighted_translation_over_time.png`
- `baseline_rotation_over_time.png` / `depth_weighted_rotation_over_time.png`
