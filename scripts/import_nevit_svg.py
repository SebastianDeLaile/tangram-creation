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
    """Find a + b*sqrt(2) ≈ value where b is a multiple of 6 (the only values
    that appear in tangram edge direction vectors)."""
    SQRT2 = math.sqrt(2)
    best = None
    for b in range(-24, 25, 6):
        a = value - b * SQRT2
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


# ---------------------------------------------------------------------------
# Edge-based placement: extract edge lines, match collinear pairs across
# pieces, average offsets for a better anchor snap than per-vertex snapping.
# ---------------------------------------------------------------------------

_EDGE_MATCH_DIST = 5.0   # max perpendicular gap between edges to try matching
_SQRT2 = math.sqrt(2)

def _edge_class_and_offset(x1: float, y1: float, x2: float, y2: float):
    """Return (angle_class, perp_offset, param_min, param_max) for a float edge.

    angle_class:  0=horizontal, 1=45°, 2=vertical, 3=135°
    perp_offset:  signed perpendicular distance from origin to the edge's line
    param_{min,max}: range along the edge's parallel axis (for overlap check)
    """
    dx, dy = x2 - x1, y2 - y1
    ang = math.atan2(dy, dx) * 180.0 / math.pi % 180.0
    cls = round(ang / 45.0) % 4
    if cls == 0:      # horizontal: offset = y, param = x
        off = (y1 + y2) / 2.0
        lo, hi = min(x1, x2), max(x1, x2)
    elif cls == 2:    # vertical: offset = x, param = y
        off = (x1 + x2) / 2.0
        lo, hi = min(y1, y2), max(y1, y2)
    elif cls == 1:    # 45°: offset = (y-x)/√2, param = (y+x)/√2
        off = ((y1 - x1) + (y2 - x2)) / 2.0 / _SQRT2
        lo = min(x1 + y1, x2 + y2) / _SQRT2
        hi = max(x1 + y1, x2 + y2) / _SQRT2
    else:             # 135°: offset = (y+x)/√2, param = (y-x)/√2
        off = ((y1 + x1) + (y2 + x2)) / 2.0 / _SQRT2
        lo = min(y1 - x1, y2 - x2) / _SQRT2
        hi = max(y1 - x1, y2 - x2) / _SQRT2
    return cls, off, lo, hi


def _snap_offset(raw_offset: float, angle_cls: int) -> Z2:
    """Snap a float edge offset to Z[√2] with b as multiple of 6.

    For horizontal/vertical offsets the value is a direct coordinate component.
    For diagonal offsets the value is (coord1 ± coord2) / √2, so we multiply
    back by √2 before snapping (which turns it into a + b√2 with integer a,b).
    """
    if angle_cls in (0, 2):   # offset is a plain coordinate
        return _snap(raw_offset)
    else:                      # offset is (coord)/√2; snap (offset * √2)
        return _snap(raw_offset * _SQRT2)


def _anchor_from_offset(snapped_coord: Z2, angle_cls: int,
                        rel_x: Z2, rel_y: Z2) -> tuple[Z2 | None, Z2 | None]:
    """Given a snapped edge-line position, return the implied (ax, ay) components.

    rel_x, rel_y are the (x, y) offset from the anchor to one vertex ON that
    edge (from exact_dirs), so: coord = anchor_component + rel_component.
    Returns (ax, None) for constraints on ax only, (None, ay) for ay only, or
    (ax, ay) for diagonal constraints expressed as a+b√2 equations.

    For diagonal angle classes the result is the SUM or DIFFERENCE of ax and ay
    encoded as a single Z2; the caller must handle this specially.
    """
    if angle_cls == 0:    # horizontal: snapped_coord = ay + rel_y
        return None, snapped_coord - rel_y
    elif angle_cls == 2:  # vertical:   snapped_coord = ax + rel_x
        return snapped_coord - rel_x, None
    else:
        # For 45° and 135° we return None, None and let the caller use the raw
        # constraint separately (handled in _solve_from_edges).
        return None, None


def _solve_from_edges(name: str, fits: list) -> list[PiecePlacement] | None:
    """Try to place all 7 pieces using collinear-edge matching.

    For every pair of edges (from different pieces) that share the same angle
    class and whose perpendicular offsets are within _EDGE_MATCH_DIST, we
    compute a consensus offset by averaging.  That consensus offset is snapped
    to Z[√2], giving us a precise edge-line position.  From each snapped edge
    we derive a constraint on the owning piece's anchor (one of ax, ay, ax±ay).

    We accumulate constraints per piece and pick the snapped anchor that best
    satisfies them, then check for zero overlap.  Returns a list of
    PiecePlacement objects if a valid placement is found, else None.
    """
    n_pieces = len(fits)

    # ---- Build float edge table ----------------------------------------
    # edge_table[fi] = list of (cls, float_off, lo, hi, rel_x_float, rel_y_float)
    #   rel_x_float, rel_y_float: midpoint of this edge RELATIVE to the float anchor
    edge_table: list[list] = []
    for fi, (pt, pid, fa, orient, flip, exact_dirs, _) in enumerate(fits):
        ax_f, ay_f = fa
        verts_f = [(ax_f, ay_f)]
        for d in exact_dirs:
            verts_f.append((ax_f + d.x.to_float(), ay_f + d.y.to_float()))
        n_v = len(verts_f)
        row = []
        for k in range(n_v):
            x1, y1 = verts_f[k]
            x2, y2 = verts_f[(k + 1) % n_v]
            cls, off, lo, hi = _edge_class_and_offset(x1, y1, x2, y2)
            rel_x = ((x1 + x2) / 2.0) - ax_f
            rel_y = ((y1 + y2) / 2.0) - ay_f
            row.append((cls, off, lo, hi, rel_x, rel_y))
        edge_table.append(row)

    # ---- Collect consensus offsets per (piece, edge) --------------------
    # consensus[fi][edge_idx] = list of float offsets from matched edges
    consensus: list[list[list[float]]] = [[[] for _ in row] for row in edge_table]

    for fi in range(n_pieces):
        for ei, (cls_i, off_i, lo_i, hi_i, _, _) in enumerate(edge_table[fi]):
            consensus[fi][ei].append(off_i)   # own estimate always included
            for fj in range(n_pieces):
                if fj == fi:
                    continue
                for ej, (cls_j, off_j, lo_j, hi_j, _, _) in enumerate(edge_table[fj]):
                    if cls_j != cls_i:
                        continue
                    if abs(off_j - off_i) > _EDGE_MATCH_DIST:
                        continue
                    # Check parameter-range overlap (edges must actually overlap
                    # in the direction parallel to the line)
                    if min(hi_i, hi_j) > max(lo_i, lo_j):
                        consensus[fi][ei].append(off_j)

    # ---- Derive anchor constraints from consensus offsets ---------------
    # For each piece, collect (ax_candidate, ay_candidate) estimates.
    # We only use horizontal (→ ay) and vertical (→ ax) edge constraints here;
    # diagonal constraints are harder to combine and rarely the binding ones.
    anchor_candidates: list[list[tuple[Z2, Z2]]] = [[] for _ in range(n_pieces)]
    for fi in range(n_pieces):
        ax_f, ay_f = fits[fi][2]
        ax_snapped = _snap(ax_f)
        ay_snapped = _snap(ay_f)
        # Build per-axis consensus snaps from horizontal/vertical edges
        ax_votes: list[Z2] = []
        ay_votes: list[Z2] = []
        for ei, (cls, off, lo, hi, rel_x, rel_y) in enumerate(edge_table[fi]):
            avg_off = sum(consensus[fi][ei]) / len(consensus[fi][ei])
            if cls == 0:     # horizontal → ay = snapped_avg - rel_y
                snapped = _snap(avg_off)
                ay_est = Z2(snapped.a - round(rel_y), snapped.b)
                ay_votes.append(ay_est)
            elif cls == 2:   # vertical → ax = snapped_avg - rel_x
                snapped = _snap(avg_off)
                ax_est = Z2(snapped.a - round(rel_x), snapped.b)
                ax_votes.append(ax_est)

        # Most-common ax and ay vote; fall back to per-vertex snap
        def _majority(votes: list[Z2], default: Z2) -> Z2:
            if not votes:
                return default
            from collections import Counter
            return Counter(str(v) for v in votes).most_common(1)[0][0]   # type: ignore[return-value]

        best_ax_str = _majority(ax_votes, ax_snapped)
        best_ay_str = _majority(ay_votes, ay_snapped)
        # Re-parse the string representation to a Z2 (Counter key is the str)
        best_ax = next((v for v in ax_votes if str(v) == best_ax_str), ax_snapped)
        best_ay = next((v for v in ay_votes if str(v) == best_ay_str), ay_snapped)
        anchor_candidates[fi].append((best_ax, best_ay))
        # Also include base snaps as fallback candidates
        anchor_candidates[fi].append((ax_snapped, ay_snapped))

    # ---- Try candidate anchors, return first with zero overlap ----------
    OVERLAP_TOLERANCE = 0.05

    def _make_pieces(anchors):
        return [PiecePlacement(fits[fi][0], fits[fi][1],
                               Point(anchors[fi][0], anchors[fi][1]),
                               fits[fi][3], fits[fi][4])
                for fi in range(n_pieces)]

    best_pieces = None
    best_ov = float("inf")
    # Enumerate candidates: each piece can use its consensus or fallback anchor
    for mask in range(1 << n_pieces):  # 2^7 = 128 combos: bit=0→consensus, bit=1→fallback
        anchors = []
        for fi in range(n_pieces):
            idx = (mask >> fi) & 1
            idx = min(idx, len(anchor_candidates[fi]) - 1)
            anchors.append(anchor_candidates[fi][idx])
        pieces = _make_pieces(anchors)
        ov = _total_overlap(pieces)
        if ov < best_ov:
            best_ov = ov
            best_pieces = pieces
        if ov <= OVERLAP_TOLERANCE:
            return pieces

    return best_pieces if best_ov <= OVERLAP_TOLERANCE else None


def _bfs_place(fits, adj, root, root_anchor: Point) -> tuple[dict[int, Point], set[int]]:
    """Returns (placed, bfs_reached) where bfs_reached are pieces derived from adjacency."""
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
    bfs_reached = set(visited)
    for fi in range(len(fits)):
        if fi not in placed:
            fa = fits[fi][2]
            placed[fi] = Point(_snap(fa[0]), _snap(fa[1]))
    return placed, bfs_reached


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
    best_bfs_reached = None
    best_overlap = float("inf")
    # Try ±1 on rational component and ±6 on irrational component (the grid step).
    # 3 × 3 × 3 × 3 = 81 candidates.
    for da in (-1, 0, 1):
        for db in (-1, 0, 1):
            for da2 in (-6, 0, 6):
                for db2 in (-6, 0, 6):
                    trial_anchor = Point(
                        Z2(base_anchor.x.a + Fraction(da), base_anchor.x.b + Fraction(da2)),
                        Z2(base_anchor.y.a + Fraction(db), base_anchor.y.b + Fraction(db2)),
                    )
                    placed, bfs_reached = _bfs_place(fits, adj, root, trial_anchor)
                    pieces = [PiecePlacement(fits[fi][0], fits[fi][1], placed[fi],
                                             fits[fi][3], fits[fi][4]) for fi in range(n_pieces)]
                    ov = _total_overlap(pieces)
                    if ov < best_overlap:
                        best_overlap = ov
                        best_placed = placed
                        best_bfs_reached = bfs_reached

    # For pieces not reachable via BFS (genuinely disconnected in the SVG), use a
    # vertex-matching heuristic: for each vertex of each placed piece, try anchors
    # that place one vertex of the disconnected piece exactly on that vertex.  This
    # is equivalent to "snap this piece so one corner touches a corner of its
    # nearest already-placed neighbour", which is almost always the right answer for
    # tangrams where the artist left a small gap between touching pieces.
    OVERLAP_TOLERANCE = 0.05
    disconnected = [fi for fi in range(n_pieces) if fi not in best_bfs_reached]
    if disconnected:
        for fi in disconnected:
            fa_x, fa_y = fits[fi][2]  # float anchor
            disc_ed = fits[fi][5]     # exact direction vectors from anchor
            # Candidate anchors: place each vertex of this piece on each vertex of
            # each already-placed piece and keep the one nearest the float position.
            placed_verts: list[Point] = []
            for fj, placed_anchor in best_placed.items():
                if fj == fi:
                    continue
                fj_ed = fits[fj][5]
                placed_verts.append(placed_anchor)
                for d in fj_ed:
                    placed_verts.append(placed_anchor + d)

            candidates: list[tuple[float, Point]] = []
            for target in placed_verts:
                # vertex 0 of fi at target → anchor = target
                candidates.append((math.dist((target.x.to_float(), target.y.to_float()), (fa_x, fa_y)), target))
                for d in disc_ed:
                    # vertex k of fi at target → anchor = target - d_k
                    cand = target - d
                    candidates.append((math.dist((cand.x.to_float(), cand.y.to_float()), (fa_x, fa_y)), cand))

            # Sort by proximity to float anchor; try in order until we find zero overlap.
            candidates.sort(key=lambda c: c[0])
            best_fi_anchor = best_placed[fi]
            best_fi_ov = _total_overlap([PiecePlacement(fits[k][0], fits[k][1], best_placed[k],
                                                        fits[k][3], fits[k][4]) for k in range(n_pieces)])
            for _, cand_anchor in candidates:
                trial_placed = {**best_placed, fi: cand_anchor}
                pieces_trial = [PiecePlacement(fits[k][0], fits[k][1], trial_placed[k],
                                               fits[k][3], fits[k][4]) for k in range(n_pieces)]
                ov = _total_overlap(pieces_trial)
                if ov < best_fi_ov:
                    best_fi_ov = ov
                    best_fi_anchor = cand_anchor
                if ov <= OVERLAP_TOLERANCE:
                    break
            best_placed[fi] = best_fi_anchor

    # Check if BFS+vertex-match gave a valid result.
    bfs_pieces = [PiecePlacement(fits[fi][0], fits[fi][1], best_placed[fi],
                                 fits[fi][3], fits[fi][4]) for fi in range(n_pieces)]
    if _total_overlap(bfs_pieces) <= OVERLAP_TOLERANCE:
        return Tangram(name=name, pieces=bfs_pieces)

    # BFS failed (disconnected pieces with real gaps).  Try the edge-based solver:
    # match collinear edges across all pieces, average their perpendicular offsets
    # for a better anchor snap, then enumerate anchor combinations.
    edge_pieces = _solve_from_edges(name, fits)
    if edge_pieces is not None and _total_overlap(edge_pieces) <= OVERLAP_TOLERANCE:
        return Tangram(name=name, pieces=edge_pieces)

    # Return the best result we found (may still have small overlaps for caller to report).
    candidate = edge_pieces if (edge_pieces and _total_overlap(edge_pieces) < _total_overlap(bfs_pieces)) else bfs_pieces
    return Tangram(name=name, pieces=candidate)


if __name__ == "__main__":
    svg_path = Path(sys.argv[1])
    polygons = extract_polygons(svg_path.read_text())
    tangram = build_tangram(svg_path.stem, polygons)
    issues = validate(tangram)
    print(f"{svg_path.name}: {'OK' if not issues else issues}")
    for p in tangram.pieces:
        print(" ", p.piece_type.value, p.piece_id, p.anchor, p.orientation, p.flipped)
