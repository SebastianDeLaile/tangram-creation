#!/usr/bin/env python3
"""Render a silhouette thumbnail for every figure and write it into
examples/index.json, so the web app's sidebar can show a picture instead of
just a title.

Each entry gains a ``thumb`` field: a small self-contained ``<svg>`` string
(explicit viewBox + width/height, filled solid) that the web app injects
directly into the shape list.

Usage:
    PYTHONPATH=src python3 scripts/gen_thumbnails.py

After writing, re-copy examples/ -> web/public/examples/ so the web app
picks up the new field (per CLAUDE.md):

    rm web/public/examples/*.json && cp examples/*.json web/public/examples/
"""
from __future__ import annotations

import json
import sys
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(REPO_ROOT / "src"))

from tangram.io import load_tangram  # noqa: E402
from tangram.model import Tangram  # noqa: E402

EXAMPLES_DIR = REPO_ROOT / "examples"
INDEX_PATH = EXAMPLES_DIR / "index.json"

MARGIN = 1.5
INK = "#2a271f"


def thumbnail_svg(tangram: Tangram) -> str:
    min_x, min_y, max_x, max_y = tangram.bounding_box()
    width = (max_x - min_x) + 2 * MARGIN
    height = (max_y - min_y) + 2 * MARGIN
    off_x = MARGIN - min_x
    off_y = MARGIN - min_y
    polys = []
    for piece in tangram.pieces:
        pts = " ".join(f"{x + off_x:.4f},{y + off_y:.4f}" for x, y in (v.to_float() for v in piece.vertices()))
        polys.append(f'<polygon points="{pts}"/>')
    body = "".join(polys)
    return (
        f'<svg viewBox="0 0 {width:.4f} {height:.4f}" width="{width:.4f}" height="{height:.4f}" '
        f'fill="{INK}" stroke="{INK}" stroke-width="0.15">{body}</svg>'
    )


def main() -> int:
    index = json.loads(INDEX_PATH.read_text())
    figures = index["figures"]

    n = 0
    for entry in figures:
        path = EXAMPLES_DIR / entry["file"]
        if not path.exists():
            print(f"  WARNING: missing figure file {entry['file']}", file=sys.stderr)
            continue
        entry["thumb"] = thumbnail_svg(load_tangram(path))
        n += 1

    INDEX_PATH.write_text(json.dumps(index, indent=2) + "\n")
    print(f"Wrote thumbnails for {n} figures to {INDEX_PATH.relative_to(REPO_ROOT)}")
    print(
        "Remember to re-copy examples -> web/public/examples so the web app "
        "sees the new field (see CLAUDE.md)."
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
