#!/usr/bin/env python3
# SI-assisted: written with Codex (OpenAI, SI tool) at a team member's direction; the team reviewed and ran it.
"""Prepare a compact global Mars map from a PDS3 MOLA MEGDR topography file.

The global layer is for overview and map navigation, not astronaut-scale route
planning. It is stored in the same south-first local array convention as the
HiRISE package, but its display coordinates are longitude/latitude degrees.
"""

from __future__ import annotations

import argparse
import hashlib
import json
import re
import sys
from pathlib import Path

try:
    import numpy as np
    from PIL import Image
except ImportError as exc:  # pragma: no cover
    raise SystemExit(
        "This tool requires NumPy and Pillow. Install with: python -m pip install numpy Pillow"
    ) from exc


def sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        while chunk := handle.read(8 * 1024 * 1024):
            digest.update(chunk)
    return digest.hexdigest()


def parse_label(path: Path) -> dict[str, int | float | str]:
    text = path.read_text(encoding="ascii", errors="replace")

    def get(name: str) -> str:
        match = re.search(rf"(?m)^\s*{re.escape(name)}\s*=\s*(.*?)\s*$", text)
        if not match:
            raise ValueError(f"missing PDS label field: {name}")
        return match.group(1).strip().strip('"')

    def number(name: str) -> float:
        return float(re.search(r"[-+]?\d+(?:\.\d+)?", get(name)).group(0))

    return {
        "lines": int(number("LINES")),
        "samples": int(number("LINE_SAMPLES")),
        "ppd": int(number("MAP_RESOLUTION")),
        "radius_km": number("A_AXIS_RADIUS"),
        "min_lat": number("MINIMUM_LATITUDE"),
        "max_lat": number("MAXIMUM_LATITUDE"),
        "west_lon": number("WESTERNMOST_LONGITUDE"),
        "east_lon": number("EASTERNMOST_LONGITUDE"),
    }


def colorize(elevation: np.ndarray, min_z: float, max_z: float) -> np.ndarray:
    """Create a compact Mars colorized-relief texture from the DEM."""
    t = np.clip((elevation - min_z) / (max_z - min_z), 0.0, 1.0)
    stops = np.array([
        [24, 32, 96],
        [26, 110, 165],
        [30, 155, 115],
        [180, 190, 70],
        [235, 145, 38],
        [176, 62, 25],
        [70, 24, 22],
    ], dtype=np.float32)
    positions = np.linspace(0.0, 1.0, len(stops))
    rgb = np.empty((*elevation.shape, 3), dtype=np.float32)
    for channel in range(3):
        rgb[..., channel] = np.interp(t, positions, stops[:, channel])

    # Add restrained hillshade so the global layer reads as terrain while
    # remaining a map texture rather than a photorealistic claim.
    gy, gx = np.gradient(elevation.astype(np.float32))
    shade = 0.76 + 0.24 * ((-gx - gy) / (np.hypot(gx, gy) + 1.0) + 1.0) / 2.0
    return np.clip(rgb * shade[..., None], 0, 255).astype(np.uint8)


def convert(args: argparse.Namespace) -> dict[str, object]:
    input_path = args.input.resolve()
    label_path = args.label.resolve() if args.label else input_path.with_suffix(".lbl")
    output_dir = args.output.resolve()
    label = parse_label(label_path)
    source_ppd = int(label["ppd"])
    if source_ppd % args.target_ppd != 0:
        raise ValueError("target ppd must evenly divide the source MAP_RESOLUTION")
    factor = source_ppd // args.target_ppd
    if args.target_ppd <= 0:
        raise ValueError("target ppd must be positive")

    shape = (int(label["lines"]), int(label["samples"]))
    expected_bytes = shape[0] * shape[1] * 2
    if input_path.stat().st_size < expected_bytes:
        raise ValueError(f"MOLA image is truncated: expected {expected_bytes} bytes")
    raw = np.memmap(input_path, dtype=">i2", mode="r", shape=shape)
    source = np.asarray(raw, dtype=np.float32)
    # PDS line 1 is northernmost; the application convention is south-first.
    source = source[::-1, :]
    out_h, out_w = shape[0] // factor, shape[1] // factor
    trimmed = source[: out_h * factor, : out_w * factor]
    dem = trimmed.reshape(out_h, factor, out_w, factor).mean(axis=(1, 3), dtype=np.float32)
    del raw, source, trimmed

    output_dir.mkdir(parents=True, exist_ok=True)
    outputs = [
        output_dir / "dem.f32",
        output_dir / "valid_mask.u8",
        output_dir / "ortho.jpg",
        output_dir / "meta.json",
    ]
    existing = [path for path in outputs if path.exists()]
    if existing and not args.force:
        raise FileExistsError(
            "refusing to overwrite " + ", ".join(path.name for path in existing) + "; use --force"
        )

    dem.astype("<f4", copy=False).tofile(outputs[0])
    np.full(dem.shape, 255, dtype=np.uint8).tofile(outputs[1])
    texture = colorize(dem, args.min_elevation, args.max_elevation)
    Image.fromarray(texture, mode="RGB").save(outputs[2], format="JPEG", quality=92, optimize=True)

    previous_meta = {}
    if outputs[3].exists():
        previous_meta = json.loads(outputs[3].read_text(encoding="utf-8"))

    cell_deg = 1.0 / args.target_ppd
    equator_m_per_degree = 2.0 * np.pi * float(label["radius_km"]) * 1000.0 / 360.0
    meta = {
        "name": "Mars global MOLA overview",
        "source": f"NASA MGS MOLA MEGDR {source_ppd} ppd → {args.target_ppd} ppd",
        "source_url": "https://pds-geosciences.wustl.edu/missions/mgs/megdr.html",
        "download_url": "https://pds-geosciences.wustl.edu/mgs/mgs-m-mola-5-megdr-l3-v1/mgsl_300x/meg016/",
        "width": out_w,
        "height": out_h,
        "cell_m": equator_m_per_degree * cell_deg,
        "base": [180.0, 90.0],
        "targets": [],
        "beacons": [],
        "format": {
            "dem": "little-endian IEEE-754 float32, row-major, south-first",
            "valid_mask": "uint8; 255=valid, 0=nodata",
        },
        "visual": {"orthophoto": "ortho.jpg", "kind": "MOLA colorized shaded relief"},
        "georeference": {
            "projection": "SIMPLE CYLINDRICAL",
            "latitude_type": "PLANETOCENTRIC",
            "positive_longitude_direction": "EAST",
            "source_resolution_ppd": source_ppd,
            "resolution_ppd": args.target_ppd,
            "cell_deg": cell_deg,
            "display_width_deg": 360.0,
            "display_height_deg": 180.0,
            "longitude_bounds_deg": [0.0, 360.0],
            "latitude_bounds_deg": [-90.0, 90.0],
            "row_order": "south-first",
        },
        "nodata": {"valid_cells": int(dem.size), "total_cells": int(dem.size), "valid_fraction": 1.0},
        "provenance": {
            "input_file": str(input_path),
            "label_file": str(label_path),
            "input_sha256": sha256(input_path),
            "label_sha256": sha256(label_path),
        },
    }
    # Keep an independently prepared Viking satellite texture when the MOLA
    # DEM is regenerated later.
    previous_visual = previous_meta.get("visual", {})
    for key in ("satellite", "satellite_kind", "satellite_source_url", "satellite_tile_url"):
        if key in previous_visual:
            meta["visual"][key] = previous_visual[key]
    if "satellite_files" in previous_meta.get("provenance", {}):
        meta["provenance"]["satellite_files"] = previous_meta["provenance"]["satellite_files"]
    outputs[3].write_text(json.dumps(meta, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    return {
        "output": str(output_dir),
        "shape": [out_w, out_h],
        "resolution_ppd": args.target_ppd,
        "cell_m_at_equator": meta["cell_m"],
        "files": [str(path) for path in outputs],
    }


def main() -> int:
    parser = argparse.ArgumentParser(description="Prepare a global MOLA overview package.")
    parser.add_argument("--input", type=Path, required=True)
    parser.add_argument("--label", type=Path)
    parser.add_argument("--output", type=Path, required=True)
    parser.add_argument("--target-ppd", type=int, default=4)
    parser.add_argument("--min-elevation", type=float, default=-8177.0)
    parser.add_argument("--max-elevation", type=float, default=21171.0)
    parser.add_argument("--force", action="store_true")
    args = parser.parse_args()
    try:
        print(json.dumps(convert(args), ensure_ascii=False, indent=2))
    except (OSError, ValueError, FileExistsError) as exc:
        print(f"preprocess_mola.py: error: {exc}", file=sys.stderr)
        return 2
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
