import json
from pathlib import Path

import pytest

from tangram.difficulty import score, stars
from tangram.io import load_tangram

EXAMPLES_DIR = Path(__file__).resolve().parent.parent / "examples"
INDEX = json.loads((EXAMPLES_DIR / "index.json").read_text())
EXAMPLE_FILES = [entry["file"] for entry in INDEX["figures"]]


@pytest.mark.parametrize("filename", EXAMPLE_FILES)
def test_every_figure_scores_1_to_5(filename):
    result = score(load_tangram(EXAMPLES_DIR / filename))
    assert 1 <= result.stars <= 5
    assert 0.0 <= result.raw <= 1.0
    assert 0.0 <= result.fill_ratio <= 1.0
    assert 0.0 <= result.orientation_variety <= 1.0


def test_assembled_square_is_hardest():
    # The base square gives zero boundary cues (convex, maximally compact), so
    # it should land at the top of the scale.
    result = score(load_tangram(EXAMPLES_DIR / "square.json"))
    assert result.convex
    assert result.stars == 5


def test_stars_are_monotonic_in_raw():
    assert stars(0.0) <= stars(0.5) <= stars(1.0)
    assert stars(0.0) == 1
    assert stars(1.0) == 5


def test_index_difficulty_matches_scorer():
    # scripts/score_difficulty.py writes the difficulty field; it must equal a
    # fresh score so a stale index.json is caught.
    for entry in INDEX["figures"]:
        expected = score(load_tangram(EXAMPLES_DIR / entry["file"])).stars
        assert entry.get("difficulty") == expected, entry["file"]
