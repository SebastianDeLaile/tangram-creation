/**
 * Vector-PDF export of print-ready puzzle cards (Part 1 v1 of docs/PRINT_PLAN.md).
 *
 * Each card is two A5 pages: page 1 is the solid-black silhouette + label, page 2
 * is the colored solution mirrored horizontally so a double-sided print (flip on
 * the long edge) lands the answer directly behind its own silhouette.
 *
 * Cards are sized for lamination + storage in a ring binder:
 * - **A5 pages**, oriented portrait or landscape to match each tangram's shape.
 * - A blank **binding gutter** down one side for hole-punching. It sits on the
 *   left of the front and the right of the (mirrored) back, i.e. the same
 *   physical edge once the sheet is flipped, so punched holes line up.
 *
 * The tangram art is embedded as true vector via svg2pdf.js (crisp at any size);
 * frame, gutter, hole guides, crop marks, captions and difficulty dots are drawn
 * with jsPDF primitives.
 */
import { jsPDF } from "jspdf";
import "svg2pdf.js";
import type { Point } from "./geometry";
import type { Tangram } from "./model";
import { PieceType } from "./pieces";
import { roundedPolygonPath } from "./roundedPath";

const SVG_NS = "http://www.w3.org/2000/svg";

export interface CardRenderOptions {
  pieceColors: Record<PieceType, string>;
  cornerRounding: number;
  fillMode: "fill" | "outline";
  gutter: boolean; // blank binding strip + hole guides down one side
}

export interface Card {
  tangram: Tangram;
  title: string;
  category: string;
  difficulty?: number;
}

// Millimetres.
const MARGIN = 9;
const GUTTER = 12; // blank binding strip for hole punches
const CAPTION_H = 14;
const TRIM = 5; // inset of the card / laminate outline from the page edge

const RULE = [140, 140, 140] as const; // cut lines / crop marks / gutter
const FAINT = [200, 200, 200] as const; // hole guides / gutter divider
const AMBER = [200, 150, 60] as const; // difficulty dots

type Orientation = "portrait" | "landscape";

interface Box {
  x: number;
  y: number;
  w: number;
  h: number;
}

function orientationFor(tangram: Tangram): Orientation {
  const [x0, y0, x1, y1] = tangram.boundingBox();
  return x1 - x0 >= y1 - y0 ? "landscape" : "portrait";
}

/** Art box for one face. When present, the gutter is on the left of the front
 *  and, mirrored, on the right of the back so both fall on the same physical
 *  binding edge. With no gutter the art box is symmetric. */
function faceLayout(pageW: number, pageH: number, mirror: boolean, gutter: number): Box {
  const y = MARGIN;
  const h = pageH - MARGIN - CAPTION_H - y;
  const frontX0 = MARGIN + gutter;
  const frontX1 = pageW - MARGIN;
  const [x0, x1] = mirror ? [pageW - frontX1, pageW - frontX0] : [frontX0, frontX1];
  return { x: x0, y, w: x1 - x0, h };
}

/** Build a detached SVG of one tangram fitted into a wPx x hPx box. */
function buildTangramSvg(
  tangram: Tangram,
  mode: "silhouette" | "solution",
  wPx: number,
  hPx: number,
  opts: CardRenderOptions,
  mirror: boolean,
): SVGSVGElement {
  const pad = Math.min(wPx, hPx) * 0.05;
  const [bx0, by0, bx1, by1] = tangram.boundingBox();
  const sw = bx1 - bx0;
  const sh = by1 - by0;
  const scale = Math.min((wPx - 2 * pad) / sw, (hPx - 2 * pad) / sh);
  const offX = (wPx - sw * scale) / 2 - bx0 * scale;
  const offY = (hPx - sh * scale) / 2 - by0 * scale;
  const toXY = (p: Point): [number, number] => {
    const [x, y] = p.toFloat();
    return [x * scale + offX, y * scale + offY];
  };
  const rounding = mode === "silhouette" ? 0 : opts.cornerRounding;

  const svg = document.createElementNS(SVG_NS, "svg");
  svg.setAttribute("xmlns", SVG_NS);
  svg.setAttribute("width", String(wPx));
  svg.setAttribute("height", String(hPx));
  svg.setAttribute("viewBox", `0 0 ${wPx} ${hPx}`);

  const group = document.createElementNS(SVG_NS, "g");
  if (mirror) group.setAttribute("transform", `translate(${wPx} 0) scale(-1 1)`);
  svg.appendChild(group);

  for (const piece of tangram.pieces) {
    const path = document.createElementNS(SVG_NS, "path");
    path.setAttribute("d", roundedPolygonPath(piece.vertices().map(toXY), rounding));
    if (mode === "silhouette") {
      path.setAttribute("fill", "#000");
      path.setAttribute("stroke", "#000");
      path.setAttribute("stroke-width", "0.5");
    } else if (opts.fillMode === "fill") {
      path.setAttribute("fill", opts.pieceColors[piece.pieceType]);
      path.setAttribute("stroke", "#1a1a1a");
      path.setAttribute("stroke-width", "1");
    } else {
      path.setAttribute("fill", "none");
      path.setAttribute("stroke", opts.pieceColors[piece.pieceType]);
      path.setAttribute("stroke-width", "4");
    }
    path.setAttribute("stroke-linejoin", "round");
    group.appendChild(path);
  }
  return svg;
}

/** Card/laminate outline + corner crop marks (trim to the A5 page). */
function drawCardOutline(doc: jsPDF, pageW: number, pageH: number): void {
  doc.setDrawColor(RULE[0], RULE[1], RULE[2]);
  doc.setLineWidth(0.2);
  doc.setLineDashPattern([], 0);
  doc.roundedRect(TRIM, TRIM, pageW - 2 * TRIM, pageH - 2 * TRIM, 3, 3);

  const len = 4;
  const corners: [number, number][] = [
    [0, 0],
    [pageW, 0],
    [0, pageH],
    [pageW, pageH],
  ];
  for (const [cx, cy] of corners) {
    const sx = cx === 0 ? 1 : -1;
    const sy = cy === 0 ? 1 : -1;
    doc.line(cx, cy + sy * 0.5, cx + sx * len, cy + sy * 0.5);
    doc.line(cx + sx * 0.5, cy, cx + sx * 0.5, cy + sy * len);
  }
}

/** Faint divider + hole guides marking the blank binding gutter. */
function drawGutter(doc: jsPDF, pageW: number, box: Box, mirror: boolean): void {
  const dividerX = mirror ? box.x + box.w : box.x; // inner edge of the gutter
  doc.setDrawColor(FAINT[0], FAINT[1], FAINT[2]);
  doc.setLineWidth(0.2);
  doc.setLineDashPattern([1, 1.5], 0);
  doc.line(dividerX, box.y, dividerX, box.y + box.h);
  doc.setLineDashPattern([], 0);

  // Two hole guides centred in the blank strip (removed when punched).
  const stripCenter = mirror ? pageW - (MARGIN + GUTTER) / 2 : (MARGIN + GUTTER) / 2;
  for (const frac of [1 / 3, 2 / 3]) {
    doc.circle(stripCenter, box.y + box.h * frac, 2, "S");
  }
}

/** A row of five dots (filled = difficulty) ending at `xRight`. */
function drawRating(doc: jsPDF, xRight: number, y: number, difficulty: number): void {
  const r = 1.0;
  const gap = 3.0;
  const xLeft = xRight - 4 * gap;
  for (let i = 0; i < 5; i++) {
    const cx = xLeft + i * gap;
    if (i < difficulty) {
      doc.setFillColor(AMBER[0], AMBER[1], AMBER[2]);
      doc.circle(cx, y, r, "F");
    } else {
      doc.setDrawColor(AMBER[0], AMBER[1], AMBER[2]);
      doc.setLineWidth(0.25);
      doc.circle(cx, y, r, "S");
    }
  }
}

function drawCaption(doc: jsPDF, box: Box, title: string, rightText: string, difficulty?: number): void {
  const baseY = box.y + box.h + 9;
  doc.setTextColor(20, 20, 20);
  doc.setFont("helvetica", "bold");
  doc.setFontSize(15);
  doc.text(title, box.x, baseY);

  const rightEdge = box.x + box.w;
  doc.setFont("helvetica", "normal");
  doc.setFontSize(9);
  doc.setTextColor(90, 90, 90);
  if (difficulty) {
    drawRating(doc, rightEdge, baseY - 1.1, difficulty);
    doc.text(rightText, rightEdge - 4 * 3.0 - 3, baseY - 1, { align: "right" });
  } else {
    doc.text(rightText, rightEdge, baseY - 1, { align: "right" });
  }
}

async function embedArt(
  doc: jsPDF,
  tangram: Tangram,
  mode: "silhouette" | "solution",
  opts: CardRenderOptions,
  mirror: boolean,
  box: Box,
): Promise<void> {
  const svg = buildTangramSvg(tangram, mode, Math.round(box.w * 4), Math.round(box.h * 4), opts, mirror);
  // svg2pdf reads live attributes; keep the node off-screen but in the document.
  const holder = document.createElement("div");
  holder.style.position = "fixed";
  holder.style.left = "-99999px";
  holder.appendChild(svg);
  document.body.appendChild(holder);
  try {
    await doc.svg(svg, { x: box.x, y: box.y, width: box.w, height: box.h });
  } finally {
    holder.remove();
  }
}

async function drawFace(
  doc: jsPDF,
  card: Card,
  mode: "silhouette" | "solution",
  mirror: boolean,
  opts: CardRenderOptions,
): Promise<void> {
  const pageW = doc.internal.pageSize.getWidth();
  const pageH = doc.internal.pageSize.getHeight();
  const box = faceLayout(pageW, pageH, mirror, opts.gutter ? GUTTER : 0);
  drawCardOutline(doc, pageW, pageH);
  if (opts.gutter) drawGutter(doc, pageW, box, mirror);
  await embedArt(doc, card.tangram, mode, opts, mirror, box);
  if (mode === "silhouette") {
    const meta = card.category ? card.category[0].toUpperCase() + card.category.slice(1) : "";
    drawCaption(doc, box, card.title, meta, card.difficulty);
  } else {
    drawCaption(doc, box, card.title, "Solution");
  }
}

/**
 * Build and download a duplex puzzle-card PDF. One card = two A5 pages (front
 * silhouette, back mirrored solution), each oriented to fit its tangram.
 * Multiple cards are emitted front/back in sequence — the correct order for
 * auto-duplex printing.
 */
export async function downloadCardsPdf(
  cards: Card[],
  opts: CardRenderOptions,
  filename: string,
): Promise<void> {
  if (cards.length === 0) return;
  const doc = new jsPDF({ unit: "mm", format: "a5", orientation: orientationFor(cards[0].tangram) });
  let started = false;
  for (const card of cards) {
    const orient = orientationFor(card.tangram);
    if (started) doc.addPage("a5", orient); // first front uses the constructor page
    started = true;
    await drawFace(doc, card, "silhouette", false, opts);
    doc.addPage("a5", orient);
    await drawFace(doc, card, "solution", true, opts);
  }
  doc.save(filename);
}
