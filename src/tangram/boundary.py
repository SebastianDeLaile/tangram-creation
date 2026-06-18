"""Extract a Tangram's outer silhouette and check whether it's convex.

The outer boundary is found by edge cancellation: with every piece wound
consistently (CCW), an edge shared between two adjacent pieces is traversed
in opposite directions by each -- so it cancels. Whatever edges are left,
once they're not also cancelled by their own mirror, trace out the outer
loop. This only gives a meaningful answer for a Tangram that already tiles
edge-to-edge with no overlaps (see validate.validate) -- a real gap or
overlap shows up here as a missing or doubled-up edge, so loop-tracing fails
loudly rather than silently returning a wrong shape.
"""
from __future__ import annotations

from .model import Tangram

Point2D = tuple[float, float]
ROUND_NDIGITS = 4


def _ensure_ccw(points: list[Point2D]) -> list[Point2D]:
    area = 0.0
    n = len(points)
    for i in range(n):
        x1, y1 = points[i]
        x2, y2 = points[(i + 1) % n]
        area += x1 * y2 - x2 * y1
    return points if area >= 0 else list(reversed(points))


def _key(p: Point2D) -> Point2D:
    return (round(p[0], ROUND_NDIGITS), round(p[1], ROUND_NDIGITS))


def _split_at_t_junctions(
    edges: list[tuple[Point2D, Point2D]], all_points: list[Point2D]
) -> list[tuple[Point2D, Point2D]]:
    """Subdivide each edge at any other piece's vertex that lies in its interior.

    Needed for T-junctions: e.g. a square's corner touching the middle of a
    parallelogram's longer edge. Without splitting, that long edge can't
    cancel against the two shorter edges on the other side, even though
    together they're the same boundary.
    """
    split: list[tuple[Point2D, Point2D]] = []
    for a, b in edges:
        ax, ay = a
        bx, by = b
        dx, dy = bx - ax, by - ay
        length_sq = dx * dx + dy * dy
        on_edge = []
        for p in all_points:
            px, py = p
            cross = dx * (py - ay) - dy * (px - ax)
            if abs(cross) > 1e-4 * max(1.0, length_sq**0.5):
                continue
            t = ((px - ax) * dx + (py - ay) * dy) / length_sq
            if 1e-6 < t < 1 - 1e-6:
                on_edge.append((t, p))
        on_edge.sort()
        chain = [a] + [p for _, p in on_edge] + [b]
        split.extend((chain[i], chain[i + 1]) for i in range(len(chain) - 1))
    return split


def boundary_edges(tangram: Tangram) -> list[tuple[Point2D, Point2D]]:
    """Directed edges that have no matching reverse edge among all pieces."""
    edges: list[tuple[Point2D, Point2D]] = []
    all_points: list[Point2D] = []
    for piece in tangram.pieces:
        poly = _ensure_ccw([v.to_float() for v in piece.vertices()])
        n = len(poly)
        edges.extend((poly[i], poly[(i + 1) % n]) for i in range(n))
        all_points.extend(poly)

    edges = _split_at_t_junctions(edges, all_points)

    reverse_counts: dict[tuple[Point2D, Point2D], int] = {}
    for a, b in edges:
        key = (_key(b), _key(a))
        reverse_counts[key] = reverse_counts.get(key, 0) + 1

    boundary = []
    for a, b in edges:
        key = (_key(a), _key(b))
        if reverse_counts.get(key, 0) > 0:
            reverse_counts[key] -= 1
        else:
            boundary.append((a, b))
    return boundary


def trace_loops(edges: list[tuple[Point2D, Point2D]]) -> list[list[Point2D]]:
    """Chain directed edges (matching endpoint-to-startpoint) into closed loops."""
    remaining = list(edges)
    loops = []
    while remaining:
        a, b = remaining.pop(0)
        loop = [a, b]
        while _key(loop[-1]) != _key(loop[0]):
            next_index = next(
                (i for i, (ca, _) in enumerate(remaining) if _key(ca) == _key(loop[-1])), None
            )
            if next_index is None:
                raise ValueError("boundary edges don't close into a loop -- tangram has a gap")
            _, cb = remaining.pop(next_index)
            loop.append(cb)
        loop.pop()
        loops.append(loop)
    return loops


def silhouette(tangram: Tangram) -> list[Point2D]:
    """The single outer-boundary polygon of a fully-tiled (no gaps/overlaps) Tangram."""
    loops = trace_loops(boundary_edges(tangram))
    if len(loops) != 1:
        raise ValueError(f"expected one outer loop, got {len(loops)} -- gap, overlap, or disconnected pieces")
    return loops[0]


def is_convex(loop: list[Point2D]) -> bool:
    n = len(loop)
    if n < 3:
        return False
    sign = 0
    for i in range(n):
        ax, ay = loop[i]
        bx, by = loop[(i + 1) % n]
        cx, cy = loop[(i + 2) % n]
        cross = (bx - ax) * (cy - by) - (by - ay) * (cx - bx)
        if abs(cross) < 1e-6:
            continue  # collinear: fine for convexity, just merge visually
        turn = 1 if cross > 0 else -1
        if sign == 0:
            sign = turn
        elif turn != sign:
            return False
    return sign != 0


def is_convex_tangram(tangram: Tangram) -> bool:
    return is_convex(silhouette(tangram))
