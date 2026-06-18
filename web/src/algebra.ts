/**
 * Exact arithmetic in Z[sqrt(2)], mirroring the Python project's algebra.py.
 *
 * Tangram pieces rotate in multiples of 45 degrees, and cos(45)=sin(45)=sqrt(2)/2,
 * so every piece vertex stays exactly representable as a + b*sqrt(2). Keeping this
 * exact (instead of floats) avoids drift across repeated drag/rotate operations.
 */
import { Fraction } from "./fraction";

export const SQRT2 = Math.SQRT2;

export class Z2 {
  constructor(readonly a: Fraction, readonly b: Fraction) {}

  static of(a: number | Fraction = 0, b: number | Fraction = 0): Z2 {
    return new Z2(Fraction.of(a), Fraction.of(b));
  }

  add(other: Z2): Z2 {
    return new Z2(this.a.add(other.a), this.b.add(other.b));
  }

  sub(other: Z2): Z2 {
    return new Z2(this.a.sub(other.a), this.b.sub(other.b));
  }

  neg(): Z2 {
    return new Z2(this.a.neg(), this.b.neg());
  }

  mul(other: Z2 | number): Z2 {
    if (other instanceof Z2) {
      // (a + b*r2)*(c + d*r2) = (ac + 2bd) + (ad + bc)*r2
      return new Z2(
        this.a.mul(other.a).add(this.b.mul(other.b).scale(2)),
        this.a.mul(other.b).add(this.b.mul(other.a)),
      );
    }
    return new Z2(this.a.scale(other), this.b.scale(other));
  }

  equals(other: Z2): boolean {
    return this.a.equals(other.a) && this.b.equals(other.b);
  }

  toFloat(): number {
    return this.a.toNumber() + this.b.toNumber() * SQRT2;
  }
}

export const ZERO = Z2.of(0, 0);
export const HALF_ROOT2 = Z2.of(0, new Fraction(1, 2));
