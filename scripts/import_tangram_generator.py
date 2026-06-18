"""Import figures from Wiebke/TangramGenerator's exampleTangrams.js.

Source: https://github.com/Wiebke/TangramGenerator (MIT licensed),
file Code/exampleTangrams.js. That project defines tans the same way this one
does -- anchor (right-angle vertex) + orientation (0-7, steps of 45deg) + a
tanType 0-5 where 4 is the parallelogram and 5 is its flipped form -- and its
canonical direction vectors are identical to pieces.CANONICAL_DIRECTIONS, so
figures translate over with no coordinate adjustment.

Usage:
    curl -s https://raw.githubusercontent.com/Wiebke/TangramGenerator/master/Code/exampleTangrams.js \
        -o /tmp/exampleTangrams.js
    python3 scripts/import_tangram_generator.py /tmp/exampleTangrams.js
"""
from __future__ import annotations

import json
import re
import sys
from fractions import Fraction
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent / "src"))

from tangram.algebra import Z2
from tangram.geometry import Point
from tangram.io import save_tangram
from tangram.model import PiecePlacement, Tangram
from tangram.pieces import PieceType
from tangram.validate import validate

TAN_TYPE_TO_PIECE = {
    0: (PieceType.LARGE_TRIANGLE, False),
    1: (PieceType.MEDIUM_TRIANGLE, False),
    2: (PieceType.SMALL_TRIANGLE, False),
    3: (PieceType.SQUARE, False),
    4: (PieceType.PARALLELOGRAM, False),
    5: (PieceType.PARALLELOGRAM, True),
}

ANCHOR_RE = re.compile(
    r"var (\w+) = new Point\(new IntAdjoinSqrt2\(([^,]+), ([^)]+)\), "
    r"new IntAdjoinSqrt2\(([^,]+), ([^)]+)\)\);"
)
TAN_RE = re.compile(r"var (\w+) = new Tan\((\d), (\w+), (\d)\);")
TANGRAM_RE = re.compile(r"var (\w+) = new Tangram\(\[([^\]]+)\]\);")
INTERESTING_RE = re.compile(r"var (interesting\d+) = '(\[.*?\])';")


def parse_js(text: str) -> dict[str, Tangram]:
    anchors: dict[str, Point] = {}
    for name, a, b, c, d in ANCHOR_RE.findall(text):
        anchors[name] = Point(Z2.of(Fraction(a), Fraction(b)), Z2.of(Fraction(c), Fraction(d)))

    tans: dict[str, tuple[int, str, int]] = {}
    for name, tan_type, anchor_name, orientation in TAN_RE.findall(text):
        tans[name] = (int(tan_type), anchor_name, int(orientation))

    tangrams: dict[str, Tangram] = {}
    for name, piece_list in TANGRAM_RE.findall(text):
        type_counters: dict[PieceType, int] = {}
        placements = []
        for var in (p.strip() for p in piece_list.split(",")):
            tan_type, anchor_name, orientation = tans[var]
            piece_type, flipped = TAN_TYPE_TO_PIECE[tan_type]
            piece_id = type_counters.get(piece_type, 0)
            type_counters[piece_type] = piece_id + 1
            placements.append(
                PiecePlacement(piece_type, piece_id, anchors[anchor_name], orientation, flipped)
            )
        tangrams[name] = Tangram(name=name, pieces=placements)

    for name, raw_json in INTERESTING_RE.findall(text):
        type_counters = {}
        placements = []
        for piece in json.loads(raw_json):
            tan_type, orientation = piece["tanType"], piece["orientation"]
            x, y = piece["anchor"]["x"], piece["anchor"]["y"]
            anchor = Point(
                Z2.of(x["coeffInt"], x["coeffSqrt"]), Z2.of(y["coeffInt"], y["coeffSqrt"])
            )
            piece_type, flipped = TAN_TYPE_TO_PIECE[tan_type]
            piece_id = type_counters.get(piece_type, 0)
            type_counters[piece_type] = piece_id + 1
            placements.append(PiecePlacement(piece_type, piece_id, anchor, orientation, flipped))
        tangrams[name] = Tangram(name=name, pieces=placements)

    return tangrams


if __name__ == "__main__":
    text = Path(sys.argv[1]).read_text()
    for name, tangram in parse_js(text).items():
        issues = validate(tangram)
        status = "OK" if not issues else f"INVALID: {issues}"
        print(f"{name}: {status}")
