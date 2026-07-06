#!/usr/bin/env python3
"""Audit the figure library for quality problems that validate() doesn't catch.

`tangram.validate` only checks piece counts and non-overlap. Two defects slip
through and are found here:

1. **Gaps** — pieces that don't tile edge-to-edge, leaving real whitespace
   between disconnected parts. Because coordinates are exact, a genuine touch is
   distance 0, so any positive minimum distance between parts is a true gap. The
   size (in the 24-unit assembled-square system) grades severity: a substantial
   separation (>= 0.9) is two floating blobs; a hairline gap is a fragile figure.

2. **Near-duplicates** — figures identical up to translation, 45-degree rotation,
   and reflection. Exact dedup misses these (different anchor/orientation); this
   canonicalises over all 16 symmetries (rounding to absorb tiny gaps) so
   rotated/mirrored copies collapse to one signature.

Usage:
    PYTHONPATH=src python3 scripts/audit_figures.py            # audit examples/
    PYTHONPATH=src python3 scripts/audit_figures.py DIR...     # audit given dirs
"""
from __future__ import annotations

import json
import math
import sys
from collections import defaultdict
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(REPO_ROOT / "src"))

from tangram.io import load_tangram  # noqa: E402
from tangram.model import Tangram  # noqa: E402

TOUCH_EPS = 1e-6
SUBSTANTIAL_GAP = 0.9  # >= this is "two shapes with substantial separation"

Point2D = tuple[float, float]


# --- gap detection --------------------------------------------------------

def _seg_seg_dist(p1: Point2D, p2: Point2D, p3: Point2D, p4: Point2D) -> float:
    def dot(a, b):
        return a[0] * b[0] + a[1] * b[1]

    def sub(a, b):
        return (a[0] - b[0], a[1] - b[1])

    def pt_seg(p, a, b):
        ab = sub(b, a)
        t = dot(sub(p, a), ab) / (dot(ab, ab) or 1e-18)
        t = max(0.0, min(1.0, t))
        c = (a[0] + t * ab[0], a[1] + t * ab[1])
        return math.hypot(p[0] - c[0], p[1] - c[1])

    return min(pt_seg(p1, p3, p4), pt_seg(p2, p3, p4), pt_seg(p3, p1, p2), pt_seg(p4, p1, p2))


def _piece_edges(tangram: Tangram, i: int) -> list[tuple[Point2D, Point2D]]:
    v = [p.to_float() for p in tangram.pieces[i].vertices()]
    return [(v[k], v[(k + 1) % len(v)]) for k in range(len(v))]


def gap(tangram: Tangram) -> tuple[float, int] | None:
    """(min gap between touch-disconnected parts, part count), or None if solid."""
    n = len(tangram.pieces)
    parent = list(range(n))

    def find(x):
        while parent[x] != x:
            parent[x] = parent[parent[x]]
            x = parent[x]
        return x

    edges = [_piece_edges(tangram, i) for i in range(n)]
    for i in range(n):
        for j in range(i + 1, n):
            if min(_seg_seg_dist(*a, *b) for a in edges[i] for b in edges[j]) < TOUCH_EPS:
                parent[find(i)] = find(j)
    comps: dict[int, list[int]] = defaultdict(list)
    for i in range(n):
        comps[find(i)].append(i)
    if len(comps) < 2:
        return None
    keys = list(comps)
    best = math.inf
    for a in range(len(keys)):
        for b in range(a + 1, len(keys)):
            for i in comps[keys[a]]:
                for j in comps[keys[b]]:
                    best = min(best, min(_seg_seg_dist(*x, *y) for x in edges[i] for y in edges[j]))
    return best, len(comps)


# --- near-duplicate detection --------------------------------------------

def _rot(x: float, y: float, k: int) -> Point2D:
    a = k * math.pi / 4
    c, s = math.cos(a), math.sin(a)
    return (x * c - y * s, x * s + y * c)


def canonical_signature(tangram: Tangram):
    """Signature invariant to translation, 45-degree rotation, and reflection."""
    pieces = [(p.piece_type.value, [v.to_float() for v in p.vertices()]) for p in tangram.pieces]
    best = None
    for mirror in (1, -1):
        for k in range(8):
            transformed = []
            allpts: list[Point2D] = []
            for typ, verts in pieces:
                tv = [_rot(mirror * x, y, k) for (x, y) in verts]
                transformed.append((typ, tv))
                allpts += tv
            minx = min(p[0] for p in allpts)
            miny = min(p[1] for p in allpts)
            sig = tuple(sorted(
                (typ, tuple(sorted((round(x - minx), round(y - miny)) for (x, y) in tv)))
                for typ, tv in transformed
            ))
            if best is None or sig < best:
                best = sig
    return best


def _figures(dirs: list[Path]) -> list[tuple[Path, str]]:
    out = []
    for d in dirs:
        index = json.loads((d / "index.json").read_text())["figures"]
        for entry in index:
            out.append((d / entry["file"], entry.get("title", entry["file"])))
    return out


def main() -> int:
    args = sys.argv[1:]
    dirs = [Path(a) for a in args] or [REPO_ROOT / "examples"]

    figures = _figures(dirs)

    print(f"== Gaps ({len(figures)} figures audited) ==")
    gaps = []
    for path, title in figures:
        info = gap(load_tangram(path))
        if info:
            gaps.append((info[0], info[1], title, path.name))
    for g, parts, title, name in sorted(gaps, key=lambda r: -r[0]):
        tier = "SUBSTANTIAL" if g >= SUBSTANTIAL_GAP else "hairline"
        print(f"  gap={g:7.3f}  {parts} parts  [{tier}]  {title} ({name})")
    if not gaps:
        print("  none")

    print(f"\n== Near-duplicate clusters ==")
    groups: dict = defaultdict(list)
    for path, title in figures:
        groups[canonical_signature(load_tangram(path))].append((title, path.name))
    clusters = [g for g in groups.values() if len(g) > 1]
    for cluster in sorted(clusters, key=lambda g: -len(g)):
        print("  " + "  ==  ".join(f"{t} ({n})" for t, n in cluster))
    if not clusters:
        print("  none")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
