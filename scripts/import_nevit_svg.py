"""Import tangram figures from Nevit Dilmen's SVG series on Wikimedia Commons.

Source: https://commons.wikimedia.org/wiki/Category:Nevit_Dilmen_Tangrams
(246 files, CC-BY-SA 3.0, by Nevit Dilmen). Each SVG is 7 straight-line
<path> polygons -- one per tangram piece -- with no inherent labelling of
piece type, orientation, or anchor. This script:

1. Parses each <path> into an absolute polygon (M/L/Z only -- these files
   have no curves).
2. Classifies each polygon as one of the 5 piece types by vertex count,
   area ratio, and side-length pattern (square: equal sides; parallelogram:
   alternating side lengths).
3. Fits anchor/orientation/flip by brute force: for every choice of which
   polygon vertex is the anchor, every 45-degree orientation, every winding
   direction, and (for the parallelogram) every flip state, check whether
   PiecePlacement(...).vertices() reproduces the polygon. With 3-4 vertices
   and 8 orientations this is a few hundred checks per piece -- cheap, and
   far more robust than deriving the transform analytically.
4. Snaps the fitted float anchor to an exact Z[sqrt(2)] value.

Usage:
    python3 scripts/import_nevit_svg.py path/to/Tangram_031_Nevit.svg
"""
from __future__ import annotations

import math
import re
import sys
from fractions import Fraction
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent / "src"))

from tangram.algebra import Z2
from tangram.geometry import Point
from tangram.model import PiecePlacement, Tangram
from tangram.pieces import CANONICAL_DIRECTIONS, PieceType
from tangram.validate import validate

FULL_SQUARE_SIDE = 24.0
FIT_TOLERANCE = 3.5  # units, after scaling -- generous because some pieces are
# hand-drawn slightly off the 45-degree grid (seen up to ~15 degrees of skew);
# kept well below the ~6.5 unit error a wrong 45-degree bucket would produce

PATH_RE = re.compile(r'<path[^>]*\sd="([^"]+)"')
TOKEN_RE = re.compile(r"([MmLlZz])|(-?\d*\.?\d+(?:[eE][-+]?\d+)?)")


def parse_path(d: str) -> list[tuple[float, float]]:
    tokens: list = []
    for m in TOKEN_RE.finditer(d):
        tokens.append(m.group(1) if m.group(1) else float(m.group(2)))

    points: list[tuple[float, float]] = []
    cur = (0.0, 0.0)
    cmd = None
    i = 0
    while i < len(tokens):
        t = tokens[i]
        if isinstance(t, str):
            cmd = t
            i += 1
            continue
        x, y = tokens[i], tokens[i + 1]
        i += 2
        if cmd in ("M", "L"):
            cur = (x, y)
        elif cmd in ("m", "l"):
            cur = (cur[0] + x, cur[1] + y)
        points.append(cur)
        if cmd == "M":
            cmd = "L"
        elif cmd == "m":
            cmd = "l"

    if len(points) > 1 and math.dist(points[0], points[-1]) < 1e-2:
        points.pop()
    return points


def extract_polygons(svg_text: str) -> list[list[tuple[float, float]]]:
    return [parse_path(d) for d in PATH_RE.findall(svg_text)]


def _side_lengths(poly: list[tuple[float, float]]) -> list[float]:
    n = len(poly)
    return [math.dist(poly[i], poly[(i + 1) % n]) for i in range(n)]


def _area(poly: list[tuple[float, float]]) -> float:
    n = len(poly)
    total = sum(poly[i][0] * poly[(i + 1) % n][1] - poly[(i + 1) % n][0] * poly[i][1] for i in range(n))
    return abs(total) / 2


def classify(polygons: list[list[tuple[float, float]]]) -> dict[PieceType, list[list[tuple[float, float]]]]:
    """Group the 7 polygons by piece type using vertex count + relative area + side pattern."""
    triangles = [p for p in polygons if len(p) == 3]
    quads = [p for p in polygons if len(p) == 4]
    if len(triangles) != 5 or len(quads) != 2:
        raise ValueError(f"expected 5 triangles + 2 quads, got {len(triangles)} + {len(quads)}")

    by_area = sorted(triangles, key=_area)
    small = by_area[:2]
    medium = [by_area[2]]
    large = by_area[3:]

    def is_square(poly):
        sides = _side_lengths(poly)
        return max(sides) - min(sides) < 0.05 * sum(sides) / len(sides)

    squares = [q for q in quads if is_square(q)]
    parallelograms = [q for q in quads if not is_square(q)]
    if len(squares) != 1 or len(parallelograms) != 1:
        raise ValueError("could not distinguish square from parallelogram")

    return {
        PieceType.LARGE_TRIANGLE: large,
        PieceType.MEDIUM_TRIANGLE: medium,
        PieceType.SMALL_TRIANGLE: small,
        PieceType.SQUARE: squares,
        PieceType.PARALLELOGRAM: parallelograms,
    }


def _snap(value: float) -> Z2:
    """Find small integers a, b with a + b*sqrt(2) ~= value."""
    best = None
    for b in range(-12, 13):
        a = value - b * math.sqrt(2)
        a_round = round(a)
        err = abs(a - a_round)
        if best is None or err < best[0]:
            best = (err, a_round, b)
    _, a, b = best
    return Z2.of(Fraction(a), Fraction(b))


def fit_piece(piece_type: PieceType, target: list[tuple[float, float]], flip_options: list[bool]):
    dirs = [d.to_float() for d in CANONICAL_DIRECTIONS[piece_type]]
    n = len(target)
    best = None
    for flip in flip_options:
        base = dirs if not flip else [(x, -y) for x, y in dirs]
        for orientation in range(8):
            theta = math.radians(orientation * 45)
            ct, st = math.cos(theta), math.sin(theta)
            rotated = [(x * ct - y * st, x * st + y * ct) for x, y in base]
            for start in range(n):
                ordered = target[start:] + target[:start]
                for seq in (ordered, [ordered[0]] + list(reversed(ordered[1:]))):
                    anchor = seq[0]
                    predicted = [anchor] + [(anchor[0] + dx, anchor[1] + dy) for dx, dy in rotated]
                    err = sum(math.dist(p, q) ** 2 for p, q in zip(predicted, seq))
                    if best is None or err < best[0]:
                        best = (err, anchor, orientation, flip)
    err, anchor, orientation, flip = best
    return math.sqrt(err / n), anchor, orientation, flip


WELD_DISTANCE = 0.5  # units; float vertex pairs within this radius are treated
# as the same tangram corner for BFS anchor propagation.


def _exact_dirs(piece_type: PieceType, orientation: int, flip: bool) -> list[Point]:
    dirs = CANONICAL_DIRECTIONS[piece_type]
    if flip:
        dirs = [Point(d.x, -d.y) for d in dirs]
    return [d.rotated_45(orientation) for d in dirs]


def build_tangram(name: str, polygons: list[list[tuple[float, float]]]) -> Tangram:
    grouped = classify(polygons)
    large_area = max(_area(p) for p in grouped[PieceType.LARGE_TRIANGLE])
    scale = math.sqrt(144.0 / large_area)  # our large-triangle area is 144

    fits = []  # (piece_type, piece_id, anchor_float, orientation, flip, exact_dirs, rmse)
    for piece_type, polys in grouped.items():
        flip_options = [False, True] if piece_type == PieceType.PARALLELOGRAM else [False]
        for piece_id, poly in enumerate(polys):
            scaled = [(x * scale, y * scale) for x, y in poly]
            rmse, anchor, orientation, flip = fit_piece(piece_type, scaled, flip_options)
            if rmse > FIT_TOLERANCE:
                raise ValueError(f"{name}: {piece_type.value}#{piece_id} fit rmse {rmse:.3f} too high")
            fits.append((piece_type, piece_id, anchor, orientation, flip,
                         _exact_dirs(piece_type, orientation, flip), rmse))

    # Float vertex table: vertex_owners[i] = (fit_index, vertex_index, float_point)
    vertex_owners = []
    for fit_index, (_, _, anchor, _, _, exact_dirs, _) in enumerate(fits):
        vertex_owners.append((fit_index, 0, anchor))
        for k, d in enumerate(exact_dirs, start=1):
            dx, dy = d.to_float()
            vertex_owners.append((fit_index, k, (anchor[0] + dx, anchor[1] + dy)))

    # Cross-piece adjacency: pairs of vertices from different pieces within WELD_DISTANCE.
    adj: dict[int, list[tuple[int, int, int]]] = {}  # fit_idx -> [(other, my_vi, other_vi)]
    for i in range(len(vertex_owners)):
        for j in range(i + 1, len(vertex_owners)):
            fi, vi, pi = vertex_owners[i]
            fj, vj, pj = vertex_owners[j]
            if fi == fj:
                continue
            if math.dist(pi, pj) < WELD_DISTANCE:
                adj.setdefault(fi, []).append((fj, vi, vj))
                adj.setdefault(fj, []).append((fi, vj, vi))

    # BFS anchor derivation: snap only the root (most accurately fit piece),
    # then derive every other piece's anchor exactly from its parent's Z[sqrt(2)]
    # vertex — no centroid averaging, so all shared corners are bit-exact consistent.
    n_pieces = len(fits)
    root = min(range(n_pieces), key=lambda i: fits[i][6])
    placed: dict[int, Point] = {}
    root_fa = fits[root][2]
    placed[root] = Point(_snap(root_fa[0]), _snap(root_fa[1]))

    queue = [root]
    visited = {root}
    while queue:
        cur = queue.pop(0)
        cur_anchor = placed[cur]
        cur_ed = fits[cur][5]
        for other, my_vi, their_vi in adj.get(cur, []):
            if other in visited:
                continue
            visited.add(other)
            shared = cur_anchor if my_vi == 0 else cur_anchor + cur_ed[my_vi - 1]
            other_ed = fits[other][5]
            placed[other] = shared if their_vi == 0 else shared - other_ed[their_vi - 1]
            queue.append(other)

    # Isolated pieces not reached by BFS: fall back to independent snap.
    for fi in range(n_pieces):
        if fi not in placed:
            fa = fits[fi][2]
            placed[fi] = Point(_snap(fa[0]), _snap(fa[1]))

    pieces = []
    for fi, (pt, pid, _, orient, flip, _, _) in enumerate(fits):
        pieces.append(PiecePlacement(pt, pid, placed[fi], orient, flip))
    return Tangram(name=name, pieces=pieces)


if __name__ == "__main__":
    svg_path = Path(sys.argv[1])
    polygons = extract_polygons(svg_path.read_text())
    tangram = build_tangram(svg_path.stem, polygons)
    issues = validate(tangram)
    print(f"{svg_path.name}: {'OK' if not issues else issues}")
    for p in tangram.pieces:
        print(" ", p.piece_type.value, p.piece_id, p.anchor, p.orientation, p.flipped)
