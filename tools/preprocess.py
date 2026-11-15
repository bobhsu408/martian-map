#!/usr/bin/env python3
# SI-assisted: written with Codex (OpenAI, SI tool) at a team member's direction; the team reviewed and ran it.
"""Convert a HiRISE PDS3 DTM IMG into the Martian Map processed format.

The output is intentionally dependency-light apart from NumPy:

    dem.f32          little-endian, row-major float32 elevations
    valid_mask.u8    255 for valid DEM cells, 0 for nodata cells
    meta.json        the fields consumed by mars-core plus provenance

The Rust engine uses a local Cartesian frame whose origin is the southwest
corner of the crop, x points east, and y points north. HiRISE PDS image lines
are normally north-to-south, so the default output flips rows to south-first.
"""

from __future__ import annotations

import argparse
import hashlib
import json
import math
import re
import struct
import sys
from pathlib import Path
from typing import Any

try:
    import numpy as np
except ImportError as exc:  # pragma: no cover - exercised by the CLI only
    raise SystemExit(
        "This tool requires NumPy. Install it with: python -m pip install numpy"
    ) from exc


FLOAT_RE = re.compile(r"[-+]?(?:\d+(?:\.\d*)?|\.\d+)(?:[Ee][-+]?\d+)?")
RADIX_RE = re.compile(r"^(\d+)#([^#]+)#$")
KEY_RE = re.compile(r"^\s*([A-Za-z0-9_^]+)\s*=\s*(.*?)\s*$")


class PdsError(ValueError):
    """Raised when the input is not a supported PDS3 HiRISE DTM."""


def _scalar_text(value: str) -> str:
    """Remove a simple PDS comment and surrounding whitespace."""
    return value.split("/*", 1)[0].strip()


def _parse_int(value: str, key: str) -> int:
    text = _scalar_text(value).strip().strip('"')
    match = RADIX_RE.match(text)
    if match:
        return int(match.group(2), int(match.group(1)))
    try:
        return int(text)
    except ValueError as exc:
        raise PdsError(f"PDS field {key} is not an integer: {value!r}") from exc


def _parse_float(value: str, key: str) -> float:
    match = FLOAT_RE.search(_scalar_text(value))
    if not match:
        raise PdsError(f"PDS field {key} is not numeric: {value!r}")
    return float(match.group(0))


def _parse_missing_constant(value: str) -> float:
    """Decode a PDS radix bit pattern such as 16#FF7FFFFB# as PC_REAL."""
    text = _scalar_text(value).strip().strip('"')
    match = RADIX_RE.match(text)
    if not match:
        return _parse_float(value, "MISSING_CONSTANT")
    base, digits = int(match.group(1)), match.group(2)
    bits = int(digits, base)
    if base == 16 and len(digits) <= 8:
        return struct.unpack("<f", struct.pack("<I", bits & 0xFFFFFFFF))[0]
    return float(bits)


def _parse_label(path: Path) -> dict[str, Any]:
    """Read the textual PDS3 label and return the fields needed by the converter."""
    with path.open("rb") as handle:
        raw = handle.read(8 * 1024 * 1024)
    text = raw.decode("ascii", errors="replace")
    end_match = re.search(r"(?m)^\s*END\s*$", text)
    if not end_match:
        raise PdsError(f"{path} does not contain a PDS3 END label marker")

    fields: dict[str, str] = {}
    for line in text[: end_match.end()].splitlines():
        match = KEY_RE.match(line)
        if match:
            fields[match.group(1).upper()] = match.group(2).strip()

    required = [
        "RECORD_BYTES",
        "^IMAGE",
        "LINES",
        "LINE_SAMPLES",
        "SAMPLE_BITS",
        "SAMPLE_TYPE",
    ]
    missing = [key for key in required if key not in fields]
    if missing:
        raise PdsError(f"missing required PDS fields: {', '.join(missing)}")

    sample_type = _scalar_text(fields["SAMPLE_TYPE"]).strip('"').upper()
    if _parse_int(fields["SAMPLE_BITS"], "SAMPLE_BITS") != 32 or sample_type != "PC_REAL":
        raise PdsError(
            "only 32-bit little-endian PC_REAL single-band DTM images are supported "
            f"(got SAMPLE_BITS={fields['SAMPLE_BITS']!r}, SAMPLE_TYPE={fields['SAMPLE_TYPE']!r})"
        )

    record_bytes = _parse_int(fields["RECORD_BYTES"], "RECORD_BYTES")
    image_record = _parse_int(fields["^IMAGE"], "^IMAGE")
    return {
        "record_bytes": record_bytes,
        "image_record": image_record,
        "data_offset": (image_record - 1) * record_bytes,
        "width": _parse_int(fields["LINE_SAMPLES"], "LINE_SAMPLES"),
        "height": _parse_int(fields["LINES"], "LINES"),
        "sample_type": sample_type,
        "missing_constant_raw": fields.get("MISSING_CONSTANT"),
        "missing_constant": (
            _parse_missing_constant(fields["MISSING_CONSTANT"])
            if fields.get("MISSING_CONSTANT")
            else None
        ),
        "valid_min": (
            _parse_float(fields["VALID_MINIMUM"], "VALID_MINIMUM")
            if fields.get("VALID_MINIMUM")
            else None
        ),
        "valid_max": (
            _parse_float(fields["VALID_MAXIMUM"], "VALID_MAXIMUM")
            if fields.get("VALID_MAXIMUM")
            else None
        ),
        "map_projection": _quoted_or_raw(fields.get("MAP_PROJECTION_TYPE")),
        "latitude_type": _quoted_or_raw(fields.get("PROJECTION_LATITUDE_TYPE")),
        "longitude_direction": _quoted_or_raw(
            fields.get("POSITIVE_LONGITUDE_DIRECTION")
        ),
        "radius_km": (
            _parse_float(fields["A_AXIS_RADIUS"], "A_AXIS_RADIUS")
            if fields.get("A_AXIS_RADIUS")
            else None
        ),
        "center_lat": (
            _parse_float(fields["CENTER_LATITUDE"], "CENTER_LATITUDE")
            if fields.get("CENTER_LATITUDE")
            else None
        ),
        "center_lon": (
            _parse_float(fields["CENTER_LONGITUDE"], "CENTER_LONGITUDE")
            if fields.get("CENTER_LONGITUDE")
            else None
        ),
        "map_scale_m": (
            _parse_float(fields["MAP_SCALE"], "MAP_SCALE")
            if fields.get("MAP_SCALE")
            else None
        ),
        "map_resolution_ppd": (
            _parse_float(fields["MAP_RESOLUTION"], "MAP_RESOLUTION")
            if fields.get("MAP_RESOLUTION")
            else None
        ),
        "min_lat": (
            _parse_float(fields["MINIMUM_LATITUDE"], "MINIMUM_LATITUDE")
            if fields.get("MINIMUM_LATITUDE")
            else None
        ),
        "max_lat": (
            _parse_float(fields["MAXIMUM_LATITUDE"], "MAXIMUM_LATITUDE")
            if fields.get("MAXIMUM_LATITUDE")
            else None
        ),
        "west_lon": (
            _parse_float(fields["WESTERNMOST_LONGITUDE"], "WESTERNMOST_LONGITUDE")
            if fields.get("WESTERNMOST_LONGITUDE")
            else None
        ),
        "east_lon": (
            _parse_float(fields["EASTERNMOST_LONGITUDE"], "EASTERNMOST_LONGITUDE")
            if fields.get("EASTERNMOST_LONGITUDE")
            else None
        ),
        "product_id": _quoted_or_raw(fields.get("PRODUCT_ID")),
    }


def _quoted_or_raw(value: str | None) -> str | None:
    if value is None:
        return None
    text = _scalar_text(value).strip()
    if len(text) >= 2 and text[0] == '"' and text[-1] == '"':
        return text[1:-1]
    return text


def _sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        while chunk := handle.read(8 * 1024 * 1024):
            digest.update(chunk)
    return digest.hexdigest()


def _require_numpy_metadata(label: dict[str, Any]) -> None:
    if label["map_scale_m"] is None:
        raise PdsError("PDS label has no MAP_SCALE; cannot construct a metric grid")
    if label["min_lat"] is None or label["max_lat"] is None:
        raise PdsError("PDS label has no latitude bounds; cannot crop by geographic center")
    if label["west_lon"] is None or label["east_lon"] is None:
        raise PdsError("PDS label has no longitude bounds; cannot crop by geographic center")


def _center_pixel(label: dict[str, Any], lat: float | None, lon: float | None) -> tuple[float, float]:
    if lat is None and lon is None:
        return (label["height"] - 1) / 2.0, (label["width"] - 1) / 2.0
    if lat is None or lon is None:
        raise PdsError("--center-lat and --center-lon must be supplied together")
    if not label["min_lat"] <= lat <= label["max_lat"]:
        raise PdsError(f"center latitude {lat} is outside the DTM bounds")
    if not label["west_lon"] <= lon <= label["east_lon"]:
        raise PdsError(f"center longitude {lon} is outside the DTM bounds")
    row = (label["max_lat"] - lat) / (label["max_lat"] - label["min_lat"])
    col = (lon - label["west_lon"]) / (label["east_lon"] - label["west_lon"])
    return row * (label["height"] - 1), col * (label["width"] - 1)


def _crop_bounds(
    label: dict[str, Any],
    center_lat: float | None,
    center_lon: float | None,
    width_m: float | None,
    height_m: float | None,
) -> tuple[int, int, int, int]:
    source_h, source_w = label["height"], label["width"]
    if width_m is None and height_m is None:
        return 0, source_h, 0, source_w
    if width_m is None:
        width_m = height_m
    if height_m is None:
        height_m = width_m
    if width_m <= 0 or height_m <= 0:
        raise PdsError("crop dimensions must be positive")

    scale = label["map_scale_m"]
    crop_w = max(1, int(round(width_m / scale)))
    crop_h = max(1, int(round(height_m / scale)))
    if crop_w > source_w or crop_h > source_h:
        raise PdsError(
            f"requested crop {crop_w}x{crop_h} pixels exceeds source {source_w}x{source_h}"
        )

    center_row, center_col = _center_pixel(label, center_lat, center_lon)
    row0 = int(round(center_row - crop_h / 2.0))
    col0 = int(round(center_col - crop_w / 2.0))
    row0 = min(max(0, row0), source_h - crop_h)
    col0 = min(max(0, col0), source_w - crop_w)
    return row0, row0 + crop_h, col0, col0 + crop_w


def _valid_mask(data: np.ndarray, label: dict[str, Any]) -> np.ndarray:
    valid = np.isfinite(data)
    missing = label.get("missing_constant")
    if missing is not None:
        valid &= data != np.asarray(missing, dtype=np.float32)
    if label.get("valid_min") is not None:
        valid &= data >= label["valid_min"]
    if label.get("valid_max") is not None:
        valid &= data <= label["valid_max"]
    return valid


def _downsample_mean(
    data: np.ndarray, valid: np.ndarray, step: int
) -> tuple[np.ndarray, np.ndarray]:
    if step == 1:
        return data.astype("<f4", copy=False), valid
    out_h, out_w = data.shape[0] // step, data.shape[1] // step
    data = data[: out_h * step, : out_w * step]
    valid = valid[: out_h * step, : out_w * step]
    blocks = data.reshape(out_h, step, out_w, step)
    valid_blocks = valid.reshape(out_h, step, out_w, step)
    counts = valid_blocks.sum(axis=(1, 3), dtype=np.int32)
    sums = np.where(valid_blocks, blocks, 0.0).sum(axis=(1, 3), dtype=np.float64)
    result = np.full((out_h, out_w), np.nan, dtype=np.float32)
    np.divide(sums, counts, out=result, where=counts > 0)
    return result, counts > 0


def _read_crop(
    input_path: Path,
    label: dict[str, Any],
    bounds: tuple[int, int, int, int],
    step: int,
    row_order: str,
) -> tuple[np.ndarray, np.ndarray]:
    row0, row1, col0, col1 = bounds
    expected_end = label["data_offset"] + label["width"] * label["height"] * 4
    actual_size = input_path.stat().st_size
    if actual_size < expected_end:
        raise PdsError(
            f"input is truncated: expected at least {expected_end} bytes, got {actual_size}"
        )
    mapped = np.memmap(
        input_path,
        dtype="<f4",
        mode="r",
        offset=label["data_offset"],
        shape=(label["height"], label["width"]),
    )
    data = np.array(mapped[row0:row1, col0:col1], dtype=np.float32, copy=True)
    del mapped
    valid = _valid_mask(data, label)
    if row_order == "south-first":
        data = np.flipud(data).copy()
        valid = np.flipud(valid).copy()
    return _downsample_mean(data, valid, step)


def _write_orthophoto(
    input_path: Path,
    output_path: Path,
    bounds: tuple[int, int, int, int],
    row_order: str,
) -> None:
    """Crop and orient the matching HiRISE orthophoto for browser texturing."""
    try:
        from PIL import Image
    except ImportError as exc:  # pragma: no cover - optional CLI path
        raise PdsError(
            "--ortho-input requires Pillow. Install it with: python -m pip install Pillow"
        ) from exc

    row0, row1, col0, col1 = bounds
    with Image.open(input_path) as image:
        image.load()
        crop = image.crop((col0, row0, col1, row1))
        if row_order == "south-first":
            transpose = getattr(Image, "Transpose", Image)
            crop = crop.transpose(transpose.FLIP_TOP_BOTTOM)
        # HiRISE RED channel is a valid grayscale satellite texture. JPEG keeps
        # the browser package much smaller than shipping the original JP2.
        if crop.mode not in ("L", "RGB"):
            crop = crop.convert("L")
        crop.save(output_path, format="JPEG", quality=92, optimize=True)


def _geo_metadata(
    label: dict[str, Any],
    bounds: tuple[int, int, int, int],
    output_shape: tuple[int, int],
    step: int,
    row_order: str,
) -> dict[str, Any]:
    row0, row1, col0, col1 = bounds
    out_h, out_w = output_shape
    lat_per_pixel = (label["max_lat"] - label["min_lat"]) / label["height"]
    lon_per_pixel = (label["east_lon"] - label["west_lon"]) / label["width"]
    south_lat = label["max_lat"] - row1 * lat_per_pixel
    north_lat = label["max_lat"] - row0 * lat_per_pixel
    west_lon = label["west_lon"] + col0 * lon_per_pixel
    east_lon = label["west_lon"] + (col0 + (col1 - col0)) * lon_per_pixel
    # The output grid is local Cartesian. These are provenance coordinates,
    # not a substitute for a full planetary CRS implementation.
    return {
        "projection": label["map_projection"],
        "latitude_type": label["latitude_type"],
        "positive_longitude_direction": label["longitude_direction"],
        "planet_radius_km": label["radius_km"],
        "source_center_lat_deg": label["center_lat"],
        "source_center_lon_deg": label["center_lon"],
        "source_bounds_deg": {
            "south": label["min_lat"],
            "north": label["max_lat"],
            "west": label["west_lon"],
            "east": label["east_lon"],
        },
        "crop_bounds_deg": {
            "south": south_lat,
            "north": north_lat,
            "west": west_lon,
            "east": east_lon,
        },
        "local_origin": {
            "latitude_deg": south_lat,
            "longitude_deg": west_lon,
            "description": "southwest corner; x=east, y=north",
        },
        "source_pixel_window": {
            "row_start": row0,
            "row_end_exclusive": row1,
            "column_start": col0,
            "column_end_exclusive": col1,
        },
        "source_row_order": "north-to-south",
        "output_row_order": row_order,
        "source_pixel_scale_m": label["map_scale_m"],
        "sample_step": step,
        "output_width_m": out_w * label["map_scale_m"] * step,
        "output_height_m": out_h * label["map_scale_m"] * step,
    }


def convert(args: argparse.Namespace) -> dict[str, Any]:
    input_path = args.input.resolve()
    output_dir = args.output.resolve()
    if not input_path.is_file():
        raise FileNotFoundError(input_path)
    label = _parse_label(input_path)
    _require_numpy_metadata(label)

    if args.sample_step < 1:
        raise PdsError("--sample-step must be >= 1")
    bounds = _crop_bounds(
        label,
        args.center_lat,
        args.center_lon,
        args.crop_width_m,
        args.crop_height_m,
    )
    data, valid = _read_crop(
        input_path, label, bounds, args.sample_step, args.row_order
    )
    valid_count = int(valid.sum())
    total_count = int(valid.size)
    if valid_count != total_count and not args.allow_nodata:
        raise PdsError(
            f"output contains {total_count - valid_count} nodata cells; "
            "choose a different crop or pass --allow-nodata explicitly"
        )

    output_dir.mkdir(parents=True, exist_ok=True)
    output_files = [output_dir / "dem.f32", output_dir / "valid_mask.u8", output_dir / "meta.json"]
    ortho_output = output_dir / "ortho.jpg" if args.ortho_input else None
    if ortho_output:
        output_files.append(ortho_output)
    existing = [path for path in output_files if path.exists()]
    if existing and not args.force:
        names = ", ".join(path.name for path in existing)
        raise FileExistsError(
            f"refusing to overwrite {names}; choose another output directory or pass --force"
        )

    dem_path, mask_path, meta_path = output_files[:3]
    data.astype("<f4", copy=False).tofile(dem_path)
    (valid.astype(np.uint8) * 255).tofile(mask_path)
    if ortho_output:
        _write_orthophoto(args.ortho_input.resolve(), ortho_output, bounds, args.row_order)

    meta = {
        # These fields are consumed by mars-core::ProcessedMeta.
        "name": args.name,
        "source": f"HiRISE DTM {label['product_id'] or input_path.stem}",
        "width": int(data.shape[1]),
        "height": int(data.shape[0]),
        "cell_m": float(label["map_scale_m"] * args.sample_step),
        "base": [float(args.base_x), float(args.base_y)],
        "targets": [],
        "beacons": [],
        # Extra fields are deliberately kept in meta.json for provenance;
        # serde ignores them when mars-core loads the required fields above.
        "format": {
            "dem": "little-endian IEEE-754 float32, row-major",
            "valid_mask": "uint8; 255=valid, 0=nodata",
        },
        "visual": {"orthophoto": "ortho.jpg" if ortho_output else None},
        "georeference": _geo_metadata(
            label, bounds, data.shape, args.sample_step, args.row_order
        ),
        "nodata": {
            "source_constant": label["missing_constant_raw"],
            "output_value": "NaN when --allow-nodata is used",
            "valid_cells": valid_count,
            "total_cells": total_count,
            "valid_fraction": valid_count / total_count if total_count else 0.0,
        },
        "provenance": {
            "input_file": str(input_path),
            "input_sha256": _sha256(input_path),
            "record_bytes": label["record_bytes"],
            "image_record": label["image_record"],
            "image_data_offset_bytes": label["data_offset"],
            "processing_tool": "tools/preprocess.py",
        },
    }
    meta_path.write_text(json.dumps(meta, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")

    return {
        "input": str(input_path),
        "output": str(output_dir),
        "shape": [int(data.shape[1]), int(data.shape[0])],
        "cell_m": meta["cell_m"],
        "valid_fraction": meta["nodata"]["valid_fraction"],
        "min": float(np.nanmin(data)) if valid_count else None,
        "max": float(np.nanmax(data)) if valid_count else None,
        "files": [str(path) for path in output_files],
    }


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        description="Convert a HiRISE PDS3 DTM .IMG into dem.f32/meta.json for mars-core."
    )
    parser.add_argument("--input", type=Path, required=True, help="HiRISE DTM .IMG file")
    parser.add_argument("--ortho-input", type=Path, help="matching HiRISE orthophoto JP2 for ortho.jpg")
    parser.add_argument("--output", type=Path, required=True, help="processed output directory")
    parser.add_argument(
        "--crop-width-m",
        type=float,
        help="crop width in metres; omit width and height to process the full DTM",
    )
    parser.add_argument("--crop-height-m", type=float, help="crop height in metres")
    parser.add_argument("--center-lat", type=float, help="crop center planetocentric latitude")
    parser.add_argument("--center-lon", type=float, help="crop center east longitude")
    parser.add_argument(
        "--sample-step",
        type=int,
        default=1,
        help="average this many source pixels per output cell (default: 1)",
    )
    parser.add_argument(
        "--row-order",
        choices=("south-first", "north-first"),
        default="south-first",
        help="output row order; south-first matches mars-core (default)",
    )
    parser.add_argument(
        "--allow-nodata",
        action="store_true",
        help="write NaN DEM cells and valid_mask.u8 instead of failing",
    )
    parser.add_argument("--name", default="HiRISE local navigation DEM")
    parser.add_argument("--base-x", type=float, default=0.0, help="base x in local metres")
    parser.add_argument("--base-y", type=float, default=0.0, help="base y in local metres")
    parser.add_argument("--force", action="store_true", help="overwrite generated output files")
    return parser


def main() -> int:
    parser = build_parser()
    args = parser.parse_args()
    try:
        summary = convert(args)
    except (FileNotFoundError, FileExistsError, PdsError, OSError) as exc:
        print(f"preprocess.py: error: {exc}", file=sys.stderr)
        return 2
    print(json.dumps(summary, ensure_ascii=False, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
