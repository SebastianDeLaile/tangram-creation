"""2D points over Z[sqrt(2)] with exact translation and 45-degree rotation."""
from __future__ import annotations

from dataclasses import dataclass

from .algebra import HALF_ROOT2, Z2


@dataclass(frozen=True)
class Point:
    x: Z2
    y: Z2

    def __add__(self, other: "Point") -> "Point":
        return Point(self.x + other.x, self.y + other.y)

    def __sub__(self, other: "Point") -> "Point":
        return Point(self.x - other.x, self.y - other.y)

    def __neg__(self) -> "Point":
        return Point(-self.x, -self.y)

    def rotated_45(self, steps: int = 1) -> "Point":
        """Rotate counter-clockwise about the origin by steps*45 degrees."""
        x, y = self.x, self.y
        for _ in range(steps % 8):
            x, y = HALF_ROOT2 * (x - y), HALF_ROOT2 * (x + y)
        return Point(x, y)

    def to_float(self) -> tuple[float, float]:
        return (self.x.to_float(), self.y.to_float())
