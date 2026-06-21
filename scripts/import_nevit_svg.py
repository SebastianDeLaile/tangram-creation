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
TOKEN_RE = re.compile(r"([MmLlHhVvZz])|(-?\d*\.?\d+(?:[eE][-+]?\d+)?)")


def _close(pts: list[tuple[float, float]]) -> list[tuple[float, float]]:
    if len(pts) > 1 and math.dist(pts[0], pts[-1]) < 1e-2:
        pts = pts[:-1]
    return pts


def parse_path(d: str) -> list[list[tuple[float, float]]]:
    """Parse SVG path data into a list of polygons (one per closed subpath).

    Handles absolute and relative M/L/H/V and Z commands; ignores curves.
    Supports both single-element-with-subpaths (Format A) and plain polygons.
    """
    tokens: list = []
    for m in TOKEN_RE.finditer(d):
        tokens.append(m.group(1) if m.group(1) else float(m.group(2)))

    subpaths: list[list[tuple[float, float]]] = []
    cur_pts: list[tuple[float, float]] = []
    cur = (0.0, 0.0)
    start = (0.0, 0.0)
    cmd = ""
    i = 0

    while i < len(tokens):
        t = tokens[i]
        if isinstance(t, str):
            cmd = t
            i += 1
            if cmd in ("Z", "z"):
                if cur_pts:
                    subpaths.append(_close(cur_pts))
                cur_pts = []
                cur = start
            continue

        if cmd in ("M", "L"):
            x, y = float(tokens[i]), float(tokens[i + 1])
            i += 2
            cur = (x, y)
            if cmd == "M":
                if cur_pts:
                    subpaths.append(_close(cur_pts))
                cur_pts = []
                start = cur
                cmd = "L"
            cur_pts.append(cur)
        elif cmd in ("m", "l"):
            x, y = float(tokens[i]), float(tokens[i + 1])
            i += 2
            cur = (cur[0] + x, cur[1] + y)
            if cmd == "m":
                if cur_pts:
                    subpaths.append(_close(cur_pts))
                cur_pts = []
                start = cur
                cmd = "l"
            cur_pts.append(cur)
        elif cmd == "H":
            cur = (float(tokens[i]), cur[1])
            i += 1
            cur_pts.append(cur)
        elif cmd == "h":
            cur = (cur[0] + float(tokens[i]), cur[1])
            i += 1
            cur_pts.append(cur)
        elif cmd == "V":
            cur = (cur[0], float(tokens[i]))
            i += 1
            cur_pts.append(cur)
        elif cmd == "v":
            cur = (cur[0], cur[1] + float(tokens[i]))
            i += 1
            cur_pts.append(cur)
        else:
            i += 1  # unhandled command token (e.g. curves) — skip one value

    if cur_pts:
        subpaths.append(_close(cur_pts))
    return subpaths


def extract_polygons(svg_text: str) -> list[list[tuple[float, float]]]:
    """Extract all piece polygons from an SVG — works for both single-path
    (all 7 pieces as subpaths of one <path>) and 7-separate-paths formats."""
    polys = []
    for d in PATH_RE.findall(svg_text):
        polys.extend(parse_path(d))
    return [p for p in polys if len(p) >= 3]


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


def _total_overlap(placements: list[PiecePlacement]) -> float:
    from tangram.validate import overlap_area
    polys = [[v.to_float() for v in p.vertices()] for p in placements]
    return sum(overlap_area(polys[i], polys[j])
               for i in range(len(polys)) for j in range(i + 1, len(polys)))


def _bfs_place(fits, adj, root, root_anchor: Point) -> dict[int, Point]:
    placed: dict[int, Point] = {root: root_anchor}
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
    for fi in range(len(fits)):
        if fi not in placed:
            fa = fits[fi][2]
            placed[fi] = Point(_snap(fa[0]), _snap(fa[1]))
    return placed


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

    n_pieces = len(fits)

    # Float vertex table for BFS adjacency.
    piece_verts: dict[int, list[tuple[int, tuple[float, float]]]] = {}
    for fit_index, (_, _, anchor, _, _, exact_dirs, _) in enumerate(fits):
        piece_verts[fit_index] = [(0, anchor)]
        for k, d in enumerate(exact_dirs, start=1):
            dx, dy = d.to_float()
            piece_verts[fit_index].append((k, (anchor[0] + dx, anchor[1] + dy)))

    # Cross-piece adjacency: for each piece-pair, keep only the CLOSEST vertex pair
    # (within WELD_DISTANCE). Using a single best-match per pair avoids the false-weld
    # problem where a too-large threshold picks the wrong vertex pair.
    adj: dict[int, list[tuple[int, int, int]]] = {}
    for fi in range(n_pieces):
        for fj in range(fi + 1, n_pieces):
            best_d = WELD_DISTANCE
            best_pair: tuple[int, int] | None = None
            for vi, pi in piece_verts[fi]:
                for vj, pj in piece_verts[fj]:
                    d = math.dist(pi, pj)
                    if d < best_d:
                        best_d = d
                        best_pair = (vi, vj)
            if best_pair is not None:
                vi, vj = best_pair
                adj.setdefault(fi, []).append((fj, vi, vj))
                adj.setdefault(fj, []).append((fi, vj, vi))

    # BFS anchor derivation: snap the root piece (best-fit), derive all others exactly.
    # Then try ±1 rational nudges of the root anchor to minimise pairwise overlap.
    root = min(range(n_pieces), key=lambda i: fits[i][6])
    root_fa = fits[root][2]
    base_anchor = Point(_snap(root_fa[0]), _snap(root_fa[1]))

    best_placed = None
    best_overlap = float("inf")
    for da in (-1, 0, 1):
        for db in (-1, 0, 1):
            trial_anchor = Point(
                Z2(base_anchor.x.a + Fraction(da), base_anchor.x.b),
                Z2(base_anchor.y.a + Fraction(db), base_anchor.y.b),
            )
            placed = _bfs_place(fits, adj, root, trial_anchor)
            pieces = [PiecePlacement(fits[fi][0], fits[fi][1], placed[fi],
                                     fits[fi][3], fits[fi][4]) for fi in range(n_pieces)]
            ov = _total_overlap(pieces)
            if ov < best_overlap:
                best_overlap = ov
                best_placed = placed

    pieces = []
    for fi, (pt, pid, _, orient, flip, _, _) in enumerate(fits):
        pieces.append(PiecePlacement(pt, pid, best_placed[fi], orient, flip))
    return Tangram(name=name, pieces=pieces)


if __name__ == "__main__":
    svg_path = Path(sys.argv[1])
    polygons = extract_polygons(svg_path.read_text())
    tangram = build_tangram(svg_path.stem, polygons)
    issues = validate(tangram)
    print(f"{svg_path.name}: {'OK' if not issues else issues}")
    for p in tangram.pieces:
        print(" ", p.piece_type.value, p.piece_id, p.anchor, p.orientation, p.flipped)
