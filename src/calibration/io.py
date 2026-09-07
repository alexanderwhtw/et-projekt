"""Calibration I/O: load the calibration image manifest, save/load results.

Filesystem I/O, deliberately separate from the pure-logic calibration
modules (corners.py, intrinsics.py, extrinsics.py, rectification.py), per
CLAUDE.md's "Logik und I/O getrennt halten".
"""

import csv
from pathlib import Path

import numpy as np
import yaml


def load_calibration_manifest(directory: Path, manifest_filename: str = "manifest.csv") -> list[dict]:
    """Parse the calibration image manifest.

    Expects the naming convention from docs/decisions.md (2026-09-04):
    `left_NNN.png` / `right_NNN.png` (NNN = 3-digit zero-padded index) plus
    a `manifest.csv` with columns `index,distanz_m,notiz,shutter,gain,timestamp`.

    Args:
        directory: folder containing the manifest and the image files
            (e.g. data/calibration_images/).
        manifest_filename: manifest file name, relative to `directory`.

    Returns:
        One dict per row, in manifest order, with the CSV columns as string
        keys plus 'left_path'/'right_path' (Path objects, existence
        verified).

    Raises:
        FileNotFoundError: the manifest or a referenced image file is missing.
    """
    directory = Path(directory)
    manifest_path = directory / manifest_filename
    if not manifest_path.is_file():
        raise FileNotFoundError(f"manifest not found: {manifest_path}")

    entries = []
    with open(manifest_path, newline="") as f:
        for row in csv.DictReader(f):
            index = int(row["index"])
            left_path = directory / f"left_{index:03d}.png"
            right_path = directory / f"right_{index:03d}.png"
            if not left_path.is_file():
                raise FileNotFoundError(f"missing image referenced in manifest: {left_path}")
            if not right_path.is_file():
                raise FileNotFoundError(f"missing image referenced in manifest: {right_path}")

            entries.append({**row, "left_path": left_path, "right_path": right_path})

    return entries


def save_calibration_result(
    path: Path,
    *,
    date: str,
    image_size: tuple[int, int],
    K_L: np.ndarray,
    dist_L: np.ndarray,
    error_L: float,
    K_R: np.ndarray,
    dist_R: np.ndarray,
    error_R: float,
    R: np.ndarray,
    T: np.ndarray,
    error_stereo: float,
    R1: np.ndarray,
    R2: np.ndarray,
    P1: np.ndarray,
    P2: np.ndarray,
    Q: np.ndarray,
) -> None:
    """Save a full calibration result (intrinsics + extrinsics + rectification) as YAML.

    One dated, self-contained file per calibration run -- not overwritten,
    see CLAUDE.md's "Ergebnis-Log" convention (results/calibration/).
    """
    data = {
        "date": date,
        "image_size": list(image_size),
        "left": {"K": np.asarray(K_L).tolist(), "dist": np.asarray(dist_L).tolist(), "reprojection_error_px": float(error_L)},
        "right": {"K": np.asarray(K_R).tolist(), "dist": np.asarray(dist_R).tolist(), "reprojection_error_px": float(error_R)},
        "stereo": {
            "R": np.asarray(R).tolist(),
            "T": np.asarray(T).tolist(),
            "baseline_m": float(np.linalg.norm(T)),
            "reprojection_error_px": float(error_stereo),
        },
        "rectification": {
            "R1": np.asarray(R1).tolist(),
            "R2": np.asarray(R2).tolist(),
            "P1": np.asarray(P1).tolist(),
            "P2": np.asarray(P2).tolist(),
            "Q": np.asarray(Q).tolist(),
        },
    }

    path = Path(path)
    path.parent.mkdir(parents=True, exist_ok=True)
    with open(path, "w") as f:
        yaml.safe_dump(data, f, default_flow_style=None, sort_keys=False)


def load_calibration_result(path: Path) -> dict:
    """Load a calibration result saved by save_calibration_result().

    Returns the same nested structure, with matrix/vector fields converted
    back to numpy arrays.
    """
    with open(path) as f:
        data = yaml.safe_load(f)

    data["image_size"] = tuple(data["image_size"])
    for camera in ("left", "right"):
        data[camera]["K"] = np.array(data[camera]["K"])
        data[camera]["dist"] = np.array(data[camera]["dist"])
    data["stereo"]["R"] = np.array(data["stereo"]["R"])
    data["stereo"]["T"] = np.array(data["stereo"]["T"])
    for key in ("R1", "R2", "P1", "P2", "Q"):
        data["rectification"][key] = np.array(data["rectification"][key])

    return data
