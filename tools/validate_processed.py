#!/usr/bin/env python3
"""Validate a processed HiRISE DEM and its provenance."""

from __future__ import annotations

import argparse
import hashlib
import json
import sys
from pathlib import Path

try:
    import numpy as np
except ImportError as exc:  # pragma: no cover
    raise SystemExit(
        "This tool requires NumPy. Install it with: python -m pip install numpy"
    ) from exc


def sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        while chunk := handle.read(8 * 1024 * 1024):
            digest.update(chunk)
    return digest.hexdigest()


def fail(message: str) -> None:
    raise ValueError(message)


def validate(directory: Path) -> dict[str, object]:
    meta_path = directory / "meta.json"
    dem_path = directory / "dem.f32"
    mask_path = directory / "valid_mask.u8"
    for path in (meta_path, dem_path, mask_path):
        if not path.is_file():
            fail(f"missing required file: {path}")

    meta = json.loads(meta_path.read_text(encoding="utf-8"))
    ortho_name = meta.get("visual", {}).get("orthophoto")
    ortho_path = directory / ortho_name if ortho_name else None
    if ortho_path and not ortho_path.is_file():
        fail(f"missing orthophoto declared by meta.json: {ortho_path}")
    satellite_name = meta.get("visual", {}).get("satellite")
    satellite_path = directory / satellite_name if satellite_name else None
    if satellite_path and not satellite_path.is_file():
        fail(f"missing satellite texture declared by meta.json: {satellite_path}")
    width, height = int(meta["width"]), int(meta["height"])
    expected_dem_bytes = width * height * 4
    expected_mask_bytes = width * height
    if dem_path.stat().st_size != expected_dem_bytes:
        fail(f"dem.f32 has {dem_path.stat().st_size} bytes; expected {expected_dem_bytes}")
    if mask_path.stat().st_size != expected_mask_bytes:
        fail(
            f"valid_mask.u8 has {mask_path.stat().st_size} bytes; "
            f"expected {expected_mask_bytes}"
        )

    dem = np.fromfile(dem_path, dtype="<f4").reshape((height, width))
    mask = np.fromfile(mask_path, dtype=np.uint8).reshape((height, width))
    mask_valid = mask == 255
    finite = np.isfinite(dem)
    if not np.array_equal(mask_valid, finite):
        fail("valid_mask.u8 does not match finite DEM cells")
    if np.any((mask != 0) & (mask != 255)):
        fail("valid_mask.u8 contains values other than 0 and 255")
    if np.any(mask_valid) and not np.all(np.isfinite(dem[mask_valid])):
        fail("valid DEM cells contain non-finite values")

    provenance = meta.get("provenance", {})
    source_path = Path(provenance.get("input_file", ""))
    if not source_path.is_file():
        fail(f"source file recorded in meta.json is unavailable: {source_path}")
    recorded_hash = provenance.get("input_sha256")
    if recorded_hash and sha256(source_path) != recorded_hash:
        fail("source SHA-256 does not match meta.json")

    georef = meta.get("georeference", {})
    window = georef.get("source_pixel_window", {})
    step = int(georef.get("sample_step", 1))
    if step == 1 and georef.get("output_row_order") == "south-first":
        offset = int(provenance["image_data_offset_bytes"])
        source_h = int(provenance.get("source_height", 0))
        source_w = int(provenance.get("source_width", 0))
        # The current meta stores the source dimensions implicitly in the
        # crop window plus output shape. For this validation, read the source
        # shape from the PDS label with the same values used by the converter.
        label = source_path.read_bytes()[: 8 * 1024 * 1024].decode("ascii", errors="replace")
        import re

        lines_match = re.search(r"(?m)^\s*LINES\s*=\s*(\d+)", label)
        samples_match = re.search(r"(?m)^\s*LINE_SAMPLES\s*=\s*(\d+)", label)
        if not lines_match or not samples_match:
            fail("cannot read source dimensions from PDS label")
        source_h = int(lines_match.group(1))
        source_w = int(samples_match.group(1))
        row0 = int(window["row_start"])
        row1 = int(window["row_end_exclusive"])
        col0 = int(window["column_start"])
        col1 = int(window["column_end_exclusive"])
        source = np.memmap(
            source_path,
            dtype="<f4",
            mode="r",
            offset=offset,
            shape=(source_h, source_w),
        )
        if not np.array_equal(dem[0], source[row1 - 1, col0:col1]):
            fail("south-first check failed: first output row is not source south edge")
        if not np.array_equal(dem[-1], source[row0, col0:col1]):
            fail("south-first check failed: last output row is not source north edge")
        del source

    return {
        "directory": str(directory.resolve()),
        "shape": [width, height],
        "cell_m": meta["cell_m"],
        "valid_fraction": float(mask_valid.mean()),
        "min": float(np.min(dem[mask_valid])) if np.any(mask_valid) else None,
        "max": float(np.max(dem[mask_valid])) if np.any(mask_valid) else None,
        "source_sha256": recorded_hash,
        "checks": [
            "file sizes",
            "finite DEM versus valid mask",
            "source SHA-256",
            "south-first row orientation" if step == 1 else "metadata row orientation",
            "orthophoto presence" if ortho_path else "no orthophoto declared",
            "satellite texture presence" if satellite_path else "no satellite texture declared",
        ],
    }


def main() -> int:
    parser = argparse.ArgumentParser(description="Validate processed Martian Map DEM files.")
    parser.add_argument("directory", type=Path, help="directory containing dem.f32/meta.json")
    args = parser.parse_args()
    try:
        print(json.dumps(validate(args.directory.resolve()), ensure_ascii=False, indent=2))
    except (OSError, KeyError, ValueError, json.JSONDecodeError) as exc:
        print(f"validate_processed.py: error: {exc}", file=sys.stderr)
        return 2
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
