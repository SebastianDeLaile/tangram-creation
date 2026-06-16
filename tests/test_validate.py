from pathlib import Path

import pytest

from tangram.algebra import Z2
from tangram.geometry import Point
from tangram.io import load_tangram
from tangram.model import PiecePlacement, Tangram
from tangram.pieces import PieceType
from tangram.validate import overlap_area, validate

EXAMPLES_DIR = Path(__file__).resolve().parent.parent / "examples"


@pytest.mark.parametrize("name", ["square", "cat", "bird", "swan"])
def test_examples_are_valid(name):
    t = load_tangram(EXAMPLES_DIR / f"{name}.json")
    assert validate(t) == []


def test_two_pieces_in_the_same_spot_overlap():
    t = Tangram(
        name="overlap",
        pieces=[
            PiecePlacement(PieceType.LARGE_TRIANGLE, 0, Point(Z2.of(0), Z2.of(0)), orientation=0),
            PiecePlacement(PieceType.LARGE_TRIANGLE, 1, Point(Z2.of(0), Z2.of(0)), orientation=0),
            PiecePlacement(PieceType.MEDIUM_TRIANGLE, 0, Point(Z2.of(0), Z2.of(0)), orientation=0),
            PiecePlacement(PieceType.SMALL_TRIANGLE, 0, Point(Z2.of(0), Z2.of(0)), orientation=0),
            PiecePlacement(PieceType.SMALL_TRIANGLE, 1, Point(Z2.of(0), Z2.of(0)), orientation=0),
            PiecePlacement(PieceType.SQUARE, 0, Point(Z2.of(0), Z2.of(0)), orientation=0),
            PiecePlacement(PieceType.PARALLELOGRAM, 0, Point(Z2.of(0), Z2.of(0)), orientation=0),
        ],
    )
    issues = validate(t)
    assert any("large_triangle#0 overlaps large_triangle#1" in issue for issue in issues)


def test_missing_piece_is_reported():
    t = Tangram(
        name="incomplete",
        pieces=[
            PiecePlacement(PieceType.LARGE_TRIANGLE, 0, Point(Z2.of(0), Z2.of(0)), orientation=0),
        ],
    )
    issues = validate(t)
    assert any("expected 2 large_triangle, got 1" in issue for issue in issues)
    assert any("expected 1 medium_triangle, got 0" in issue for issue in issues)


def test_duplicate_id_is_reported():
    t = Tangram(
        name="dup_ids",
        pieces=[
            PiecePlacement(PieceType.LARGE_TRIANGLE, 0, Point(Z2.of(0), Z2.of(0)), orientation=0),
            PiecePlacement(PieceType.LARGE_TRIANGLE, 0, Point(Z2.of(10), Z2.of(10)), orientation=0),
        ],
    )
    issues = validate(t)
    assert any("large_triangle ids should be [0, 1], got [0]" in issue for issue in issues)


def test_overlap_area_of_disjoint_squares_is_zero():
    square_a = [(0.0, 0.0), (1.0, 0.0), (1.0, 1.0), (0.0, 1.0)]
    square_b = [(5.0, 5.0), (6.0, 5.0), (6.0, 6.0), (5.0, 6.0)]
    assert overlap_area(square_a, square_b) == 0.0


def test_overlap_area_of_identical_squares_is_full_area():
    square = [(0.0, 0.0), (2.0, 0.0), (2.0, 2.0), (0.0, 2.0)]
    assert overlap_area(square, square) == pytest.approx(4.0)


def test_overlap_area_of_half_overlapping_squares():
    square_a = [(0.0, 0.0), (2.0, 0.0), (2.0, 2.0), (0.0, 2.0)]
    square_b = [(1.0, 0.0), (3.0, 0.0), (3.0, 2.0), (1.0, 2.0)]
    assert overlap_area(square_a, square_b) == pytest.approx(2.0)
