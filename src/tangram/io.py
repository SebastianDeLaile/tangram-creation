"""Load and save Tangram configurations as JSON, preserving exact Z[sqrt(2)] values."""
from __future__ import annotations

import json
from fractions import Fraction
from pathlib import Path

from .algebra import Z2
from .geometry import Point
from .model import PiecePlacement, Tangram
from .pieces import PieceType


def _fraction_to_json(value: Fraction):
    return value.numerator if value.denominator == 1 else str(value)


def _fraction_from_json(value) -> Fraction:
    return Fraction(value)


def _z2_to_json(z: Z2) -> list:
    return [_fraction_to_json(z.a), _fraction_to_json(z.b)]


def _z2_from_json(data: list) -> Z2:
    a, b = data
    return Z2.of(_fraction_from_json(a), _fraction_from_json(b))


def _piece_to_dict(piece: PiecePlacement) -> dict:
    return {
        "piece": piece.piece_type.value,
        "id": piece.piece_id,
        "anchor": {
            "x": _z2_to_json(piece.anchor.x),
            "y": _z2_to_json(piece.anchor.y),
        },
        "orientation": piece.orientation,
        "flipped": piece.flipped,
    }


def _piece_from_dict(data: dict) -> PiecePlacement:
    anchor = Point(_z2_from_json(data["anchor"]["x"]), _z2_from_json(data["anchor"]["y"]))
    return PiecePlacement(
        piece_type=PieceType(data["piece"]),
        piece_id=data["id"],
        anchor=anchor,
        orientation=data.get("orientation", 0),
        flipped=data.get("flipped", False),
    )


def tangram_to_dict(tangram: Tangram) -> dict:
    d: dict = {
        "name": tangram.name,
        "description": tangram.description,
        "pieces": [_piece_to_dict(p) for p in tangram.pieces],
    }
    if tangram.source:
        d["source"] = tangram.source
    return d


def tangram_from_dict(data: dict) -> Tangram:
    return Tangram(
        name=data["name"],
        description=data.get("description", ""),
        source=data.get("source", ""),
        pieces=[_piece_from_dict(p) for p in data["pieces"]],
    )


def save_tangram(tangram: Tangram, path: str | Path) -> None:
    Path(path).write_text(json.dumps(tangram_to_dict(tangram), indent=2) + "\n")


def load_tangram(path: str | Path) -> Tangram:
    return tangram_from_dict(json.loads(Path(path).read_text()))
