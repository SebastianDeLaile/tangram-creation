"""Render a Tangram to SVG."""
from __future__ import annotations

from .model import Tangram
from .pieces import PIECE_COLORS

MARGIN = 2.0


def render_svg(tangram: Tangram, stroke: str = "#1a1a1a", stroke_width: float = 0.3) -> str:
    min_x, min_y, max_x, max_y = tangram.bounding_box()
    width = (max_x - min_x) + 2 * MARGIN
    height = (max_y - min_y) + 2 * MARGIN
    offset_x = MARGIN - min_x
    offset_y = MARGIN - min_y

    polygons = []
    for piece in tangram.pieces:
        points = " ".join(
            f"{x + offset_x:.4f},{y + offset_y:.4f}"
            for x, y in (v.to_float() for v in piece.vertices())
        )
        color = PIECE_COLORS[piece.piece_type]
        polygons.append(
            f'<polygon points="{points}" fill="{color}" '
            f'stroke="{stroke}" stroke-width="{stroke_width}" />'
        )

    body = "\n  ".join(polygons)
    return (
        f'<svg xmlns="http://www.w3.org/2000/svg" '
        f'viewBox="0 0 {width:.4f} {height:.4f}" '
        f'width="{width:.0f}" height="{height:.0f}">\n'
        f'  <rect width="100%" height="100%" fill="white" />\n'
        f"  {body}\n"
        f"</svg>\n"
    )


def save_svg(tangram: Tangram, path: str) -> None:
    with open(path, "w") as f:
        f.write(render_svg(tangram))
