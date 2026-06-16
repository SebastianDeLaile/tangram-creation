import json
from pathlib import Path

import pytest

from tangram.algebra import Z2
from tangram.geometry import Point
from tangram.io import load_tangram, save_tangram, tangram_from_dict, tangram_to_dict
from tangram.model import PiecePlacement, Tangram
from tangram.pieces import PieceType

EXAMPLES_DIR = Path(__file__).resolve().parent.parent / "examples"


@pytest.mark.parametrize("name", ["square", "cat", "bird", "swan"])
def test_examples_load_with_seven_pieces(name):
    t = load_tangram(EXAMPLES_DIR / f"{name}.json")
    assert len(t.pieces) == 7


def test_round_trip_preserves_exact_coordinates(tmp_path):
    original = Tangram(
        name="test",
        pieces=[
            PiecePlacement(
                PieceType.LARGE_TRIANGLE, 0,
                Point(Z2.of(18, 12), Z2.of(30, -6)),
                orientation=3, flipped=False,
            )
        ],
    )
    path = tmp_path / "round_trip.json"
    save_tangram(original, path)
    loaded = load_tangram(path)
    assert loaded.pieces[0].anchor == original.pieces[0].anchor
    assert loaded.pieces[0].orientation == original.pieces[0].orientation


def test_json_stores_plain_integers_not_floats(tmp_path):
    t = Tangram(
        name="test",
        pieces=[
            PiecePlacement(PieceType.SQUARE, 0, Point(Z2.of(6, 0), Z2.of(6, 0)), orientation=1)
        ],
    )
    path = tmp_path / "ints.json"
    save_tangram(t, path)
    raw = json.loads(path.read_text())
    assert raw["pieces"][0]["anchor"]["x"] == [6, 0]


def test_dict_round_trip():
    t = load_tangram(EXAMPLES_DIR / "cat.json")
    assert tangram_from_dict(tangram_to_dict(t)).pieces == t.pieces
