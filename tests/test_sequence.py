import csv

from src.capture.sequence import append_manifest_row, build_frame_paths, next_free_index


def test_build_frame_paths_naming(tmp_path):
    left, right = build_frame_paths(tmp_path, 7)
    assert left == tmp_path / "left_007.png"
    assert right == tmp_path / "right_007.png"


def test_next_free_index_empty_directory(tmp_path):
    assert next_free_index(tmp_path) == 0


def test_next_free_index_skips_used_indices(tmp_path):
    (tmp_path / "left_000.png").touch()
    (tmp_path / "left_001.png").touch()
    assert next_free_index(tmp_path) == 2


def test_next_free_index_fills_gaps(tmp_path):
    (tmp_path / "left_000.png").touch()
    (tmp_path / "left_002.png").touch()
    assert next_free_index(tmp_path) == 1  # smallest free index, not just max+1


def test_append_manifest_row_writes_header_once_then_appends(tmp_path):
    fieldnames = ["index", "distanz_m", "notiz"]
    append_manifest_row(tmp_path, {"index": 0, "distanz_m": 1.0, "notiz": "frontal"}, fieldnames)
    append_manifest_row(tmp_path, {"index": 1, "distanz_m": 1.5, "notiz": "gekippt"}, fieldnames)

    with open(tmp_path / "manifest.csv", newline="") as f:
        rows = list(csv.DictReader(f))

    assert len(rows) == 2
    assert rows[0]["notiz"] == "frontal"
    assert rows[1]["distanz_m"] == "1.5"
