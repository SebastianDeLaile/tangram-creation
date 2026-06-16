from fractions import Fraction

from tangram.algebra import SQRT2, Z2


def test_z2_addition():
    assert Z2.of(1, 2) + Z2.of(3, 4) == Z2.of(4, 6)


def test_z2_multiplication():
    # (1 + sqrt2)(1 - sqrt2) = 1 - 2 = -1
    assert Z2.of(1, 1) * Z2.of(1, -1) == Z2.of(-1, 0)


def test_z2_scalar_multiplication():
    assert Z2.of(2, 3) * 2 == Z2.of(4, 6)


def test_z2_to_float():
    z = Z2.of(1, 1)
    assert abs(z.to_float() - (1 + SQRT2)) < 1e-12


def test_z2_supports_fractions():
    z = Z2.of(Fraction(1, 2), Fraction(1, 2))
    assert z.a == Fraction(1, 2)
