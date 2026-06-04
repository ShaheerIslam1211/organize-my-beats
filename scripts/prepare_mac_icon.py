#!/usr/bin/env python3
"""Prepare a macOS app icon from one or more source PNGs."""

from __future__ import annotations

import sys
from pathlib import Path

from PIL import Image

CANVAS = 1024

ICONSET_SIZES = {
    "icon_16x16.png": 16,
    "icon_16x16@2x.png": 32,
    "icon_32x32.png": 32,
    "icon_32x32@2x.png": 64,
    "icon_128x128.png": 128,
    "icon_128x128@2x.png": 256,
    "icon_256x256.png": 256,
    "icon_256x256@2x.png": 512,
    "icon_512x512.png": 512,
    "icon_512x512@2x.png": 1024,
}


def load_sources(paths: list[Path]) -> dict[int, Image.Image]:
    """Load PNG sources keyed by their pixel width (must be square)."""
    sources: dict[int, Image.Image] = {}
    for path in paths:
        with Image.open(path) as img:
            img = img.convert("RGBA")
        if img.width != img.height:
            raise ValueError(f"Icon must be square: {path} ({img.width}x{img.height})")
        sources[img.width] = img.copy()
    if not sources:
        raise ValueError("No icon sources provided")
    return sources


def pick_source(sources: dict[int, Image.Image], target: int) -> Image.Image:
    """Pick the sharpest source for a target size (exact match preferred)."""
    if target in sources:
        return sources[target]

    sizes = sorted(sources)
    larger = [size for size in sizes if size >= target]
    if larger:
        return sources[min(larger)]
    return sources[max(sizes)]


def resize_icon(img: Image.Image, target: int) -> Image.Image:
    """Resize icon to target square using high-quality filtering."""
    if img.width == target:
        return img.copy()

    if img.width > target:
        resample = Image.Resampling.LANCZOS
    else:
        # Upscale only when no larger source exists.
        resample = Image.Resampling.LANCZOS

    return img.resize((target, target), resample)


def prepare_master(sources: dict[int, Image.Image], output: Path) -> None:
    """Build the 1024px master from the largest available source."""
    source = pick_source(sources, CANVAS)
    master = resize_icon(source, CANVAS)
    output.parent.mkdir(parents=True, exist_ok=True)
    master.save(output, format="PNG", optimize=True)


def write_iconset(sources: dict[int, Image.Image], iconset_dir: Path) -> None:
    """Generate every iconset PNG using the best native source per size."""
    iconset_dir.mkdir(parents=True, exist_ok=True)

    for filename, size in ICONSET_SIZES.items():
        source = pick_source(sources, size)
        icon = resize_icon(source, size)
        icon.save(iconset_dir / filename, format="PNG", optimize=True)


def main() -> int:
    if len(sys.argv) < 4:
        print(
            "Usage: prepare_mac_icon.py <master.png> <iconset_dir> <source1.png> [source2.png ...]",
            file=sys.stderr,
        )
        return 1

    master = Path(sys.argv[1])
    iconset_dir = Path(sys.argv[2])
    source_paths = [Path(p) for p in sys.argv[3:]]

    missing = [p for p in source_paths if not p.exists()]
    if missing:
        for path in missing:
            print(f"Source icon not found: {path}", file=sys.stderr)
        return 1

    sources = load_sources(source_paths)
    largest = max(sources)
    print(f"Using icon sources: {sorted(sources)}px (largest: {largest}px)")

    prepare_master(sources, master)
    write_iconset(sources, iconset_dir)
    print(f"Prepared master icon: {master}")
    print(f"Generated iconset in: {iconset_dir}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
