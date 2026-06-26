/** A tangram configuration: where each of the 7 pieces sits. */
import { Point } from "./geometry";
import { directionsFor, PieceType } from "./pieces";

export class PiecePlacement {
  constructor(
    readonly pieceType: PieceType,
    readonly pieceId: number, // 0, or 1 for the second copy of a duplicated piece
    readonly anchor: Point,
    readonly orientation: number = 0, // multiples of 45 degrees, 0-7
    readonly flipped: boolean = false, // only meaningful for PieceType.Parallelogram
  ) {}

  /** Polygon vertices in order, starting at the anchor. */
  vertices(): Point[] {
    const dirs = directionsFor(this.pieceType, this.flipped);
    return [this.anchor, ...dirs.map((d) => this.anchor.add(d.rotated45(this.orientation)))];
  }

  rotated(steps: number = 1): PiecePlacement {
    return new PiecePlacement(
      this.pieceType,
      this.pieceId,
      this.anchor,
      ((this.orientation + steps) % 8 + 8) % 8,
      this.flipped,
    );
  }

  translated(delta: Point): PiecePlacement {
    return new PiecePlacement(
      this.pieceType,
      this.pieceId,
      this.anchor.add(delta),
      this.orientation,
      this.flipped,
    );
  }

  withAnchor(anchor: Point): PiecePlacement {
    return new PiecePlacement(this.pieceType, this.pieceId, anchor, this.orientation, this.flipped);
  }

  flippedCopy(): PiecePlacement {
    return new PiecePlacement(this.pieceType, this.pieceId, this.anchor, this.orientation, !this.flipped);
  }
}

export class Tangram {
  constructor(
    public name: string,
    public pieces: PiecePlacement[] = [],
    public description: string = "",
    public source: string = "",
    // Some real figures are drawn as several intentionally-separated parts (e.g. a
    // candle flame above the body); such figures set this and skip the connectivity check.
    public allowDisconnected: boolean = false,
  ) {}

  /** [min_x, min_y, max_x, max_y] over all piece vertices. */
  boundingBox(): [number, number, number, number] {
    const xs: number[] = [];
    const ys: number[] = [];
    for (const piece of this.pieces) {
      for (const v of piece.vertices()) {
        const [x, y] = v.toFloat();
        xs.push(x);
        ys.push(y);
      }
    }
    return [Math.min(...xs), Math.min(...ys), Math.max(...xs), Math.max(...ys)];
  }
}
