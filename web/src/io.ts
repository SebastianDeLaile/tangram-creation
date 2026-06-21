/**
 * Parse/serialize Tangram configurations to/from the same JSON schema used by
 * the Python project's io.py, preserving exact Z[sqrt(2)] values.
 */
import { Z2 } from "./algebra";
import { Fraction } from "./fraction";
import { Point } from "./geometry";
import { PiecePlacement, Tangram } from "./model";
import { PieceType } from "./pieces";

type JsonNum = number | string;

interface PieceJson {
  piece: string;
  id: number;
  anchor: { x: [JsonNum, JsonNum]; y: [JsonNum, JsonNum] };
  orientation: number;
  flipped: boolean;
}

interface TangramJson {
  name: string;
  description?: string;
  source?: string;
  pieces: PieceJson[];
}

function z2FromJson([a, b]: [JsonNum, JsonNum]): Z2 {
  return new Z2(Fraction.fromJSON(a), Fraction.fromJSON(b));
}

function z2ToJson(z: Z2): [JsonNum, JsonNum] {
  return [z.a.toJSON(), z.b.toJSON()];
}

function pieceFromJson(data: PieceJson): PiecePlacement {
  const anchor = new Point(z2FromJson(data.anchor.x), z2FromJson(data.anchor.y));
  return new PiecePlacement(
    data.piece as PieceType,
    data.id,
    anchor,
    data.orientation ?? 0,
    data.flipped ?? false,
  );
}

function pieceToJson(piece: PiecePlacement): PieceJson {
  return {
    piece: piece.pieceType,
    id: piece.pieceId,
    anchor: { x: z2ToJson(piece.anchor.x), y: z2ToJson(piece.anchor.y) },
    orientation: piece.orientation,
    flipped: piece.flipped,
  };
}

export function tangramFromJson(data: TangramJson): Tangram {
  return new Tangram(data.name, data.pieces.map(pieceFromJson), data.description ?? "", data.source ?? "");
}

export function tangramToJson(tangram: Tangram): TangramJson {
  const obj: TangramJson = {
    name: tangram.name,
    description: tangram.description,
    pieces: tangram.pieces.map(pieceToJson),
  };
  if (tangram.source) obj.source = tangram.source;
  return obj;
}

export async function loadTangram(url: string): Promise<Tangram> {
  const response = await fetch(url);
  if (!response.ok) throw new Error(`Failed to load ${url}: ${response.status}`);
  return tangramFromJson(await response.json());
}

export interface IndexEntry {
  file: string;
  title?: string;
  category: string;
  source: string;
  tags: string[];
}

export async function loadIndex(url: string): Promise<IndexEntry[]> {
  const response = await fetch(url);
  if (!response.ok) throw new Error(`Failed to load ${url}: ${response.status}`);
  const data = await response.json();
  return data.figures as IndexEntry[];
}
