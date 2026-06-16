"""Canonical tan geometry: shape and size of each piece type at orientation 0.

The square assembled from all 7 pieces has side length 24. This scale keeps every
piece vertex, at any multiple-of-45-degree rotation, exactly representable in
Z[sqrt(2)] (see algebra.py) -- no irrational leftovers, no float drift.
"""
from __future__ import annotations

from enum import Enum

from .algebra import Z2
from .geometry import Point


class PieceType(Enum):
    LARGE_TRIANGLE = "large_triangle"
    MEDIUM_TRIANGLE = "medium_triangle"
    SMALL_TRIANGLE = "small_triangle"
    SQUARE = "square"
    PARALLELOGRAM = "parallelogram"


def _pt(ax, ax2, ay, ay2) -> Point:
    return Point(Z2.of(ax, ax2), Z2.of(ay, ay2))


# Direction vectors from a piece's anchor (its right-angle vertex, for
# triangles) to its remaining vertices, at orientation 0, before any flip.
CANONICAL_DIRECTIONS: dict[PieceType, list[Point]] = {
    PieceType.LARGE_TRIANGLE: [
        _pt(0, 12, 0, 0),
        _pt(0, 0, 0, 12),
    ],
    PieceType.MEDIUM_TRIANGLE: [
        _pt(12, 0, 0, 0),
        _pt(0, 0, 12, 0),
    ],
    PieceType.SMALL_TRIANGLE: [
        _pt(0, 6, 0, 0),
        _pt(0, 0, 0, 6),
    ],
    PieceType.SQUARE: [
        _pt(0, 6, 0, 0),
        _pt(0, 6, 0, 6),
        _pt(0, 0, 0, 6),
    ],
    PieceType.PARALLELOGRAM: [
        _pt(12, 0, 0, 0),
        _pt(18, 0, 6, 0),
        _pt(6, 0, 6, 0),
    ],
}

# How many copies of each piece type a full tangram has.
PIECE_COUNTS: dict[PieceType, int] = {
    PieceType.LARGE_TRIANGLE: 2,
    PieceType.MEDIUM_TRIANGLE: 1,
    PieceType.SMALL_TRIANGLE: 2,
    PieceType.SQUARE: 1,
    PieceType.PARALLELOGRAM: 1,
}

# Display colors, loosely matching common tangram color schemes.
PIECE_COLORS: dict[PieceType, str] = {
    PieceType.LARGE_TRIANGLE: "#e74c3c",
    PieceType.MEDIUM_TRIANGLE: "#f1c40f",
    PieceType.SMALL_TRIANGLE: "#3498db",
    PieceType.SQUARE: "#2ecc71",
    PieceType.PARALLELOGRAM: "#9b59b6",
}


def directions_for(piece_type: PieceType, flipped: bool = False) -> list[Point]:
    """Direction vectors for a piece, mirrored across the anchor's first edge if flipped.

    Only the parallelogram is asymmetric under this mirroring; flipping any other
    piece type yields the same shape, so callers should only set flipped=True for
    PieceType.PARALLELOGRAM.
    """
    dirs = CANONICAL_DIRECTIONS[piece_type]
    if not flipped:
        return dirs
    return [Point(p.x, -p.y) for p in dirs]
