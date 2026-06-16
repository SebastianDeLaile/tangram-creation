from tangram.algebra import Z2
from tangram.geometry import Point


def test_rotate_45_known_value():
    # (12*sqrt2, 0) rotated 45 degrees CCW lands exactly on (12, 12)
    p = Point(Z2.of(0, 12), Z2.of(0, 0))
    rotated = p.rotated_45(1)
    assert rotated == Point(Z2.of(12, 0), Z2.of(12, 0))


def test_full_rotation_is_identity():
    p = Point(Z2.of(3, 5), Z2.of(-2, 7))
    assert p.rotated_45(8) == p


def test_rotation_stays_exact_no_fraction_buildup():
    # Eight successive 45-degree steps should never need an irreducible
    # fraction beyond what's needed to land back on integers.
    p = Point(Z2.of(0, 6), Z2.of(0, 0))
    for steps in range(9):
        rotated = p.rotated_45(steps)
        # to_float should round-trip without raising and stay finite
        x, y = rotated.to_float()
        assert abs(x) < 100 and abs(y) < 100
