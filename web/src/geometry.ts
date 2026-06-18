/** 2D points over Z[sqrt(2)] with exact translation and 45-degree rotation. */
import { HALF_ROOT2, Z2 } from "./algebra";

export class Point {
  constructor(readonly x: Z2, readonly y: Z2) {}

  add(other: Point): Point {
    return new Point(this.x.add(other.x), this.y.add(other.y));
  }

  sub(other: Point): Point {
    return new Point(this.x.sub(other.x), this.y.sub(other.y));
  }

  neg(): Point {
    return new Point(this.x.neg(), this.y.neg());
  }

  /** Rotate counter-clockwise about the origin by steps*45 degrees. */
  rotated45(steps: number): Point {
    let x = this.x;
    let y = this.y;
    const n = ((steps % 8) + 8) % 8;
    for (let i = 0; i < n; i++) {
      const nx = HALF_ROOT2.mul(x.sub(y));
      const ny = HALF_ROOT2.mul(x.add(y));
      x = nx;
      y = ny;
    }
    return new Point(x, y);
  }

  toFloat(): [number, number] {
    return [this.x.toFloat(), this.y.toFloat()];
  }

  equals(other: Point): boolean {
    return this.x.equals(other.x) && this.y.equals(other.y);
  }
}
