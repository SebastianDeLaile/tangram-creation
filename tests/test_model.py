from pathlib import Path

from tangram.algebra import Z2
from tangram.geometry import Point
from tangram.model import PiecePlacement, Tangram
from tangram.pieces import PieceType

EXAMPLES_DIR = Path(__file__).resolve().parent.parent / "examples"


def _shoelace_area(vertices: list[Point]) -> float:
    total = 0.0
    n = len(vertices)
    for i in range(n):
        x1, y1 = vertices[i].to_float()
        x2, y2 = vertices[(i + 1) % n].to_float()
        total += x1 * y2 - x2 * y1
    return abs(total) / 2


def test_piece_rotated_returns_new_placement():
    p = PiecePlacement(PieceType.SQUARE, 0, Point(Z2.of(0, 0), Z2.of(0, 0)), orientation=0)
    rotated = p.rotated(2)
    assert rotated.orientation == 2
    assert p.orientation == 0  # original unchanged


def test_piece_translated():
    p = PiecePlacement(PieceType.SQUARE, 0, Point(Z2.of(0, 0), Z2.of(0, 0)))
    moved = p.translated(Point(Z2.of(3, 0), Z2.of(4, 0)))
    assert moved.anchor == Point(Z2.of(3, 0), Z2.of(4, 0))


def test_parallelogram_flip_changes_shape():
    p = PiecePlacement(PieceType.PARALLELOGRAM, 0, Point(Z2.of(0, 0), Z2.of(0, 0)))
    flipped = p.flipped_copy()
    assert flipped.flipped is True
    assert p.vertices() != flipped.vertices()


def test_full_square_tangram_area_is_576():
    from tangram.io import load_tangram

    t = load_tangram(EXAMPLES_DIR / "square.json")
    total_area = sum(_shoelace_area(piece.vertices()) for piece in t.pieces)
    assert abs(total_area - 576) < 1e-9


def test_bounding_box_matches_square_extents():
    from tangram.io import load_tangram

    t = load_tangram(EXAMPLES_DIR / "square.json")
    assert t.bounding_box() == (0.0, 0.0, 24.0, 24.0)
