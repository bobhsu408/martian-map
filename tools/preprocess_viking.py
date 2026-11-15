#!/usr/bin/env python3
# SI-assisted: written with Codex (OpenAI, SI tool) at a team member's direction; the team reviewed and ran it.
"""Stitch the official ASU/NASA Viking global color mosaic thumbnails.

The source is a simple-cylindrical global mosaic split into four longitude
tiles for each hemisphere. This compact package is intended as an offline
overview texture; it is not a navigation-resolution image.
"""

from __future__ import annotations

import argparse
import hashlib
import json
from pathlib import Path

from PIL import Image


SOURCE_URL = "https://www.mars.asu.edu/data/mdim_color/"
TILE_URL = "https://www.mars.asu.edu/data/mdim_color/"
ORDER = (
    "mars45n045.png",
    "mars45n135.png",
    "mars45n225.png",
    "mars45n315.png",
    "mars45s045.png",
    "mars45s135.png",
    "mars45s225.png",
    "mars45s315.png",
)


def sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        while chunk := handle.read(1024 * 1024):
            digest.update(chunk)
    return digest.hexdigest()


def convert(args: argparse.Namespace) -> dict[str, object]:
    source_dir = args.input.resolve()
    output_dir = args.output.resolve()
    source_paths = [source_dir / name for name in ORDER]
    missing = [str(path) for path in source_paths if not path.exists()]
    if missing:
        raise FileNotFoundError("missing Viking tiles: " + ", ".join(missing))

    def image_size(path: Path) -> tuple[int, int]:
        with Image.open(path) as image:
            return image.size

    source_tile_size = image_size(source_paths[0])
    if any(image_size(path) != source_tile_size for path in source_paths):
        raise ValueError("all Viking tiles must have the same dimensions")
    scale = min(1.0, args.max_width / (source_tile_size[0] * 4))
    tile_size = (max(1, round(source_tile_size[0] * scale)), max(1, round(source_tile_size[1] * scale)))

    output_dir.mkdir(parents=True, exist_ok=True)
    output_path = output_dir / "satellite.jpg"
    meta_path = output_dir / "meta.json"
    if output_path.exists() and not args.force:
        raise FileExistsError(f"refusing to overwrite {output_path}; use --force")

    mosaic = Image.new("RGB", (tile_size[0] * 4, tile_size[1] * 2))
    for index, path in enumerate(source_paths):
        with Image.open(path) as source_tile:
            tile = source_tile.convert("RGB")
            if tile.size != tile_size:
                tile = tile.resize(tile_size, Image.Resampling.LANCZOS)
            row = 0 if index < 4 else 1
            col = index if index < 4 else index - 4
            mosaic.paste(tile, (col * tile_size[0], row * tile_size[1]))
    mosaic.save(output_path, format="JPEG", quality=94, optimize=True)

    meta = json.loads(meta_path.read_text(encoding="utf-8")) if meta_path.exists() else {}
    visual = meta.setdefault("visual", {})
    visual.update({
        "satellite": "satellite.jpg",
        "satellite_kind": "NASA Viking merged color mosaic",
        "satellite_source_url": SOURCE_URL,
        "satellite_tile_url": TILE_URL + ("large/" if source_tile_size[0] > 1000 else "small/"),
        "satellite_dimensions": [mosaic.width, mosaic.height],
        "satellite_source_tile_dimensions": list(source_tile_size),
    })
    provenance = meta.setdefault("provenance", {})
    provenance["satellite_files"] = [
        {"name": path.name, "sha256": sha256(path)} for path in source_paths
    ]
    meta_path.write_text(json.dumps(meta, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    return {
        "output": str(output_path),
        "shape": [mosaic.width, mosaic.height],
        "source_url": SOURCE_URL,
    }


def main() -> int:
    parser = argparse.ArgumentParser(description="Stitch Viking global satellite overview tiles.")
    parser.add_argument("--input", type=Path, required=True, help="directory containing the 8 downloaded PNG tiles")
    parser.add_argument("--output", type=Path, required=True)
    parser.add_argument("--max-width", type=int, default=8192,
                        help="maximum output width; avoids exceeding browser texture limits")
    parser.add_argument("--force", action="store_true")
    args = parser.parse_args()
    result = convert(args)
    print(json.dumps(result, ensure_ascii=False, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
