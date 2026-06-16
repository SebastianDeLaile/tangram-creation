"""A tangram configuration: where each of the 7 pieces sits."""
from __future__ import annotations

from dataclasses import dataclass, field

from .geometry import Point
from .pieces import PieceType, directions_for


@dataclass(frozen=True)
class PiecePlacement:
    piece_type: PieceType
    piece_id: int  # 0, or 1 for the second copy of a duplicated piece
    anchor: Point
    orientation: int = 0  # multiples of 45 degrees, 0-7
    flipped: bool = False  # only meaningful for PieceType.PARALLELOGRAM

    def vertices(self) -> list[Point]:
        """Polygon vertices in order, starting at the anchor."""
        dirs = directions_for(self.piece_type, self.flipped)
        return [self.anchor] + [
            self.anchor + d.rotated_45(self.orientation) for d in dirs
        ]

    def rotated(self, steps: int = 1) -> "PiecePlacement":
        return PiecePlacement(
            self.piece_type, self.piece_id, self.anchor,
            (self.orientation + steps) % 8, self.flipped,
        )

    def translated(self, delta: Point) -> "PiecePlacement":
        return PiecePlacement(
            self.piece_type, self.piece_id, self.anchor + delta,
            self.orientation, self.flipped,
        )

    def flipped_copy(self) -> "PiecePlacement":
        return PiecePlacement(
            self.piece_type, self.piece_id, self.anchor,
            self.orientation, not self.flipped,
        )


@dataclass
class Tangram:
    name: str
    pieces: list[PiecePlacement] = field(default_factory=list)
    description: str = ""

    def bounding_box(self) -> tuple[float, float, float, float]:
        """(min_x, min_y, max_x, max_y) over all piece vertices."""
        xs: list[float] = []
        ys: list[float] = []
        for piece in self.pieces:
            for v in piece.vertices():
                fx, fy = v.to_float()
                xs.append(fx)
                ys.append(fy)
        return (min(xs), min(ys), max(xs), max(ys))
