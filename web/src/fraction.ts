/** Exact rational arithmetic, mirroring Python's fractions.Fraction. */
export class Fraction {
  readonly num: number;
  readonly den: number;

  constructor(num: number, den: number = 1) {
    if (den === 0) throw new Error("Fraction denominator cannot be 0");
    if (den < 0) {
      num = -num;
      den = -den;
    }
    const g = Fraction.gcd(Math.abs(num), den) || 1;
    this.num = num / g;
    this.den = den / g;
  }

  private static gcd(a: number, b: number): number {
    while (b !== 0) {
      [a, b] = [b, a % b];
    }
    return a;
  }

  static of(value: number | Fraction): Fraction {
    return value instanceof Fraction ? value : new Fraction(value, 1);
  }

  add(other: Fraction): Fraction {
    return new Fraction(this.num * other.den + other.num * this.den, this.den * other.den);
  }

  sub(other: Fraction): Fraction {
    return new Fraction(this.num * other.den - other.num * this.den, this.den * other.den);
  }

  neg(): Fraction {
    return new Fraction(-this.num, this.den);
  }

  mul(other: Fraction): Fraction {
    return new Fraction(this.num * other.num, this.den * other.den);
  }

  scale(factor: number): Fraction {
    return this.mul(new Fraction(factor, 1));
  }

  equals(other: Fraction): boolean {
    return this.num === other.num && this.den === other.den;
  }

  toNumber(): number {
    return this.num / this.den;
  }

  toString(): string {
    return this.den === 1 ? `${this.num}` : `${this.num}/${this.den}`;
  }

  toJSON(): number | string {
    return this.den === 1 ? this.num : this.toString();
  }

  static fromJSON(value: number | string): Fraction {
    if (typeof value === "number") return new Fraction(value, 1);
    const [num, den] = value.split("/").map(Number);
    return new Fraction(num, den ?? 1);
  }
}
