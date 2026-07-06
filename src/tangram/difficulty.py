"""Auto-estimate how hard a Tangram figure is to solve, from the exact model.

Difficulty is a heuristic derived entirely from geometry -- no hand-labeling.
Real tangram difficulty correlates with a few computable properties:

- **Convexity** -- convex silhouettes (there are only 13 convex tangrams) give
  almost no boundary cues, so they're famously the hardest.
- **Compactness** -- the 7 pieces always total area 576, so the fill ratio
  ``576 / bounding-box area`` says how tightly packed the figure is. Compact
  blobs hide piece placements; spindly shapes telegraph them.
- **Silhouette perimeter** -- a shorter outline (relative to the assembled
  square's perimeter of 96) means fewer notches and corners to key off, so it's
  harder. Long, spiky outlines are easier.
- **Orientation variety** -- how many distinct 45-degree orientations the
  pieces use, plus whether the parallelogram is flipped. More variety means
  subtler placements.

``score`` returns all sub-metrics plus a combined ``raw`` in [0, 1]; ``stars``
buckets that into a 1-5 rating. The sub-metrics are deliberately exposed so the
weighting can be tuned and spot-checked against known easy/hard figures.
"""
from __future__ import annotations

import math
from dataclasses import dataclass

from .boundary import is_convex, silhouette
from .model import Tangram

# The 7 tans always tile the unit square, so a valid figure's area is constant.
TOTAL_PIECE_AREA = 576.0  # 24 x 24
ASSEMBLED_SQUARE_PERIMETER = 96.0  # 4 x 24

# Weights for combining sub-metrics into the raw score (must sum to 1.0).
W_FILL = 0.35
W_PERIMETER = 0.20
W_CONVEX = 0.25
W_ORIENTATION = 0.20


@dataclass(frozen=True)
class Difficulty:
    stars: int  # 1-5, the headline rating
    raw: float  # combined score in [0, 1]
    convex: bool
    fill_ratio: float  # 576 / bbox area, clamped to [0, 1]
    perimeter_compactness: float  # 96 / silhouette perimeter, clamped to [0, 1]
    orientation_variety: float  # [0, 1]
    connected: bool  # False for allow_disconnected figures (silhouette N/A)


def _polygon_perimeter(loop: list[tuple[float, float]]) -> float:
    n = len(loop)
    return sum(
        math.dist(loop[i], loop[(i + 1) % n]) for i in range(n)
    )


def _orientation_variety(tangram: Tangram) -> float:
    orientations = {p.orientation % 8 for p in tangram.pieces}
    # 7 pieces, so 1..7 distinct values; map (distinct-1)/6 -> [0, 1].
    variety = (len(orientations) - 1) / 6.0
    flipped = any(p.flipped for p in tangram.pieces)
    return min(1.0, variety + (0.15 if flipped else 0.0))


def _fill_ratio(tangram: Tangram) -> float:
    min_x, min_y, max_x, max_y = tangram.bounding_box()
    bbox_area = (max_x - min_x) * (max_y - min_y)
    if bbox_area <= 0:
        return 0.0
    return min(1.0, TOTAL_PIECE_AREA / bbox_area)


def score(tangram: Tangram) -> Difficulty:
    """Estimate a figure's difficulty from its geometry alone."""
    fill_ratio = _fill_ratio(tangram)
    orientation_variety = _orientation_variety(tangram)

    # Silhouette tracing only works for a single-loop (connected) figure. Some
    # library figures are intentionally drawn as separated parts
    # (allow_disconnected); for those we skip the outline-based metrics rather
    # than fail, and treat them as non-convex with neutral perimeter.
    try:
        loop = silhouette(tangram)
        connected = True
        convex = is_convex(loop)
        perimeter = _polygon_perimeter(loop)
        perimeter_compactness = (
            min(1.0, ASSEMBLED_SQUARE_PERIMETER / perimeter) if perimeter > 0 else 0.0
        )
    except ValueError:
        connected = False
        convex = False
        perimeter_compactness = 0.5  # neutral: no outline to judge

    raw = (
        W_FILL * fill_ratio
        + W_PERIMETER * perimeter_compactness
        + W_CONVEX * (1.0 if convex else 0.0)
        + W_ORIENTATION * orientation_variety
    )

    return Difficulty(
        stars=stars(raw),
        raw=raw,
        convex=convex,
        fill_ratio=fill_ratio,
        perimeter_compactness=perimeter_compactness,
        orientation_variety=orientation_variety,
        connected=connected,
    )


# Thresholds mapping the raw [0, 1] score to 1-5 stars. Tuned so the library
# spreads across all five buckets rather than clumping; see
# scripts/score_difficulty.py --stats to re-inspect the distribution.
_STAR_THRESHOLDS = (0.34, 0.40, 0.46, 0.60)


def stars(raw: float) -> int:
    for i, threshold in enumerate(_STAR_THRESHOLDS):
        if raw < threshold:
            return i + 1
    return 5
