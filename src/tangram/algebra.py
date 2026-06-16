"""Exact arithmetic in Z[sqrt(2)], the ring of numbers a + b*sqrt(2) with a, b rational.

Tangram pieces rotate in multiples of 45 degrees, and cos(45) = sin(45) = sqrt(2)/2.
Representing coordinates as (a, b) pairs instead of floats means every rotation,
translation, and comparison stays exact -- no accumulated floating point drift
across repeated transforms.
"""
from __future__ import annotations

from dataclasses import dataclass
from fractions import Fraction
from numbers import Rational

SQRT2 = 2 ** 0.5


def _as_fraction(value) -> Fraction:
    if isinstance(value, Fraction):
        return value
    return Fraction(value)


@dataclass(frozen=True)
class Z2:
    """a + b*sqrt(2)."""

    a: Fraction
    b: Fraction

    @staticmethod
    def of(a: Rational = 0, b: Rational = 0) -> "Z2":
        return Z2(_as_fraction(a), _as_fraction(b))

    def __add__(self, other: "Z2") -> "Z2":
        return Z2(self.a + other.a, self.b + other.b)

    def __sub__(self, other: "Z2") -> "Z2":
        return Z2(self.a - other.a, self.b - other.b)

    def __neg__(self) -> "Z2":
        return Z2(-self.a, -self.b)

    def __mul__(self, other) -> "Z2":
        if isinstance(other, Z2):
            # (a + b*r2)*(c + d*r2) = (ac + 2bd) + (ad + bc)*r2
            return Z2(
                self.a * other.a + 2 * self.b * other.b,
                self.a * other.b + self.b * other.a,
            )
        scalar = _as_fraction(other)
        return Z2(self.a * scalar, self.b * scalar)

    __rmul__ = __mul__

    def to_float(self) -> float:
        return float(self.a) + float(self.b) * SQRT2

    def __repr__(self) -> str:
        return f"Z2({self.a}, {self.b})"


ZERO = Z2.of(0, 0)
HALF_ROOT2 = Z2.of(0, Fraction(1, 2))  # cos(45deg) == sin(45deg)
