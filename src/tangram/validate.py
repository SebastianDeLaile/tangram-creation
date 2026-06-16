"""Check that a Tangram is a legal placement: right pieces, no overlaps.

Overlap is checked by clipping each pair of (convex) piece polygons against
each other and measuring the area of what's left. Floats are fine here --
this is a final sanity check, not a step in a chain of transforms, so there's
no drift to accumulate.
"""
from __future__ import annotations

from collections import Counter

from .model import Tangram
from .pieces import PIECE_COUNTS

OVERLAP_TOLERANCE = 1e-6  # area units, on a square of side 24 (area 576)

Point2D = tuple[float, float]


def polygon_area(points: list[Point2D]) -> float:
    area = 0.0
    n = len(points)
    for i in range(n):
        x1, y1 = points[i]
        x2, y2 = points[(i + 1) % n]
        area += x1 * y2 - x2 * y1
    return area / 2


def _ensure_ccw(points: list[Point2D]) -> list[Point2D]:
    return points if polygon_area(points) >= 0 else list(reversed(points))


def _segment_intersection(p1: Point2D, p2: Point2D, q1: Point2D, q2: Point2D) -> Point2D:
    """Where line p1->p2 crosses line q1->q2. Callers only call this when they cross."""
    x1, y1 = p1
    x2, y2 = p2
    x3, y3 = q1
    x4, y4 = q2
    denom = (x1 - x2) * (y3 - y4) - (y1 - y2) * (x3 - x4)
    t = ((x1 - x3) * (y3 - y4) - (y1 - y3) * (x3 - x4)) / denom
    return (x1 + t * (x2 - x1), y1 + t * (y2 - y1))


def _clip_to_edge(subject: list[Point2D], edge_start: Point2D, edge_end: Point2D) -> list[Point2D]:
    """Sutherland-Hodgman: keep the part of `subject` left of directed edge_start->edge_end."""
    ex, ey = edge_end[0] - edge_start[0], edge_end[1] - edge_start[1]

    def inside(p: Point2D) -> bool:
        return ex * (p[1] - edge_start[1]) - ey * (p[0] - edge_start[0]) >= -1e-9

    output: list[Point2D] = []
    n = len(subject)
    for i in range(n):
        cur, prev = subject[i], subject[i - 1]
        cur_in, prev_in = inside(cur), inside(prev)
        if cur_in != prev_in:
            output.append(_segment_intersection(prev, cur, edge_start, edge_end))
        if cur_in:
            output.append(cur)
    return output


def convex_intersection(poly_a: list[Point2D], poly_b: list[Point2D]) -> list[Point2D]:
    """Intersection polygon of two convex polygons, both wound CCW."""
    result = poly_a
    n = len(poly_b)
    for i in range(n):
        result = _clip_to_edge(result, poly_b[i - 1], poly_b[i])
        if not result:
            return []
    return result


def overlap_area(poly_a: list[Point2D], poly_b: list[Point2D]) -> float:
    inter = convex_intersection(_ensure_ccw(poly_a), _ensure_ccw(poly_b))
    return polygon_area(inter) if len(inter) >= 3 else 0.0


def validate(tangram: Tangram) -> list[str]:
    """Return a list of human-readable problems; empty means the tangram is legal."""
    issues: list[str] = []

    type_counts = Counter(p.piece_type for p in tangram.pieces)
    for piece_type, expected in PIECE_COUNTS.items():
        actual = type_counts.get(piece_type, 0)
        if actual != expected:
            issues.append(f"expected {expected} {piece_type.value}, got {actual}")

    ids_by_type: dict = {}
    for p in tangram.pieces:
        ids_by_type.setdefault(p.piece_type, set()).add(p.piece_id)
    for piece_type, expected in PIECE_COUNTS.items():
        want = set(range(expected))
        got = ids_by_type.get(piece_type, set())
        if got != want:
            issues.append(f"{piece_type.value} ids should be {sorted(want)}, got {sorted(got)}")

    polys = [[v.to_float() for v in p.vertices()] for p in tangram.pieces]
    for i in range(len(polys)):
        for j in range(i + 1, len(polys)):
            area = overlap_area(polys[i], polys[j])
            if area > OVERLAP_TOLERANCE:
                pa, pb = tangram.pieces[i], tangram.pieces[j]
                issues.append(
                    f"{pa.piece_type.value}#{pa.piece_id} overlaps "
                    f"{pb.piece_type.value}#{pb.piece_id} (area={area:.4f})"
                )
    return issues
