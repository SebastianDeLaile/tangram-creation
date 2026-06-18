/**
 * Canonical tan geometry, mirroring the Python project's pieces.py.
 *
 * The square assembled from all 7 pieces has side length 24, the scale that
 * keeps every piece vertex exactly representable in Z[sqrt(2)] at any
 * multiple-of-45-degree rotation.
 */
import { Z2 } from "./algebra";
import { Point } from "./geometry";

export enum PieceType {
  LargeTriangle = "large_triangle",
  MediumTriangle = "medium_triangle",
  SmallTriangle = "small_triangle",
  Square = "square",
  Parallelogram = "parallelogram",
}

function pt(ax: number, ax2: number, ay: number, ay2: number): Point {
  return new Point(Z2.of(ax, ax2), Z2.of(ay, ay2));
}

// Direction vectors from a piece's anchor (its right-angle vertex, for
// triangles) to its remaining vertices, at orientation 0, before any flip.
export const CANONICAL_DIRECTIONS: Record<PieceType, Point[]> = {
  [PieceType.LargeTriangle]: [pt(0, 12, 0, 0), pt(0, 0, 0, 12)],
  [PieceType.MediumTriangle]: [pt(12, 0, 0, 0), pt(0, 0, 12, 0)],
  [PieceType.SmallTriangle]: [pt(0, 6, 0, 0), pt(0, 0, 0, 6)],
  [PieceType.Square]: [pt(0, 6, 0, 0), pt(0, 6, 0, 6), pt(0, 0, 0, 6)],
  [PieceType.Parallelogram]: [pt(12, 0, 0, 0), pt(18, 0, 6, 0), pt(6, 0, 6, 0)],
};

export const PIECE_COUNTS: Record<PieceType, number> = {
  [PieceType.LargeTriangle]: 2,
  [PieceType.MediumTriangle]: 1,
  [PieceType.SmallTriangle]: 2,
  [PieceType.Square]: 1,
  [PieceType.Parallelogram]: 1,
};

export const PIECE_COLORS: Record<PieceType, string> = {
  [PieceType.LargeTriangle]: "#e74c3c",
  [PieceType.MediumTriangle]: "#f1c40f",
  [PieceType.SmallTriangle]: "#3498db",
  [PieceType.Square]: "#2ecc71",
  [PieceType.Parallelogram]: "#9b59b6",
};

/**
 * Direction vectors for a piece, mirrored across the anchor's first edge if
 * flipped. Only the parallelogram is asymmetric under this mirroring.
 */
export function directionsFor(pieceType: PieceType, flipped: boolean): Point[] {
  const dirs = CANONICAL_DIRECTIONS[pieceType];
  if (!flipped) return dirs;
  return dirs.map((p) => new Point(p.x, p.y.neg()));
}
