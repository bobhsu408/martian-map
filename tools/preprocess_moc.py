#!/usr/bin/env python3
"""Prepare one MOC Atlas regional tile for the Mars map viewer."""

from __future__ import annotations

import argparse
import hashlib
import json
from pathlib import Path

from PIL import Image


SOURCE_URL = "https://www.mars.asu.edu/data/moc_256/"


def sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        while chunk := handle.read(1024 * 1024):
            digest.update(chunk)
    return digest.hexdigest()


def convert(args: argparse.Namespace) -> dict[str, object]:
    source = args.input.resolve()
    output_dir = args.output.resolve()
    output_dir.mkdir(parents=True, exist_ok=True)
    output = output_dir / "moc.jpg"
    meta_path = output_dir / "meta.json"
    if not source.is_file():
        raise FileNotFoundError(source)
    if output.exists() and not args.force:
        raise FileExistsError(f"refusing to overwrite {output}; use --force")

    with Image.open(source) as image:
        image.convert("L").save(output, format="JPEG", quality=95, optimize=True)
        width, height = image.size

    meta = {
        "name": "Gale region MOC Atlas",
        "source": "NASA MGS/MOC Atlas 256 pixels/degree",
        "source_url": SOURCE_URL,
        "width": width,
        "height": height,
        "visual": {
            "satellite": "moc.jpg",
            "satellite_kind": "MOC visible-light wide-angle regional mosaic",
        },
        "georeference": {
            "projection": "SIMPLE CYLINDRICAL",
            "latitude_type": "PLANETOCENTRIC",
            "positive_longitude_direction": "EAST",
            "longitude_bounds_deg": [120.0, 150.0],
            "latitude_bounds_deg": [-30.0, 0.0],
            "cell_deg": 30.0 / width,
            "row_order": "north-first",
        },
        "provenance": {
            "input_file": str(source),
            "input_sha256": sha256(source),
        },
    }
    meta_path.write_text(json.dumps(meta, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    return {"output": str(output), "shape": [width, height], "source_url": SOURCE_URL}


def main() -> int:
    parser = argparse.ArgumentParser(description="Prepare a regional MOC Atlas tile.")
    parser.add_argument("--input", type=Path, required=True)
    parser.add_argument("--output", type=Path, required=True)
    parser.add_argument("--force", action="store_true")
    args = parser.parse_args()
    print(json.dumps(convert(args), ensure_ascii=False, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
