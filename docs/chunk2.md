# Chunk 2 — Geometry fixes

You edit **individual figure `.json` files only** — do **not** touch
`examples/index.json` (Chunk 1 owns it). That keeps you conflict-free and parallel.

## Shared context (read first)

- Coordinates are exact values in ℤ[√2] (`tangram.algebra.Z2`, `a + b√2` backed by
  `fractions.Fraction`) — never plain floats. A figure is a `Tangram` of 7
  `PiecePlacement`s (`piece_type`, `piece_id`, `anchor: Point`, `orientation` 0–7 in
  45° steps, `flipped`). Load/save with `tangram.io.load_tangram` / `save_tangram`.
- Piece dimensions: large-tri legs 12√2, medium-tri legs 12, small-tri legs 6√2,
  square side 6√2, parallelogram 12×6. Whole set area 576.
- Every edited figure must still pass `tangram.validate.validate()` (7 correct
  pieces, no overlaps, connected — unless it legitimately sets
  `allow_disconnected=True`). Run `.venv/bin/pytest tests/ -q`.
- After editing `examples/<f>.json`, mirror it: `cp examples/<f>.json
  web/public/examples/<f>.json`.
- Render to check your work (with piece edges) — see `scripts/find_duplicates.py`
  for the cairosvg pattern.
- **Worked example**: the Moose cleanup (git `505fe3c`) moves one piece by an exact
  ℤ[√2] translation so it shares an edge with the body. To translate a piece,
  add a `Z2` delta to both anchor components; to rotate a piece 180° about a point
  `C`, set `new_anchor = 2C − anchor` and `orientation = (orientation+4) % 8`
  (use `2C = min_corner + max_corner`, which stays exact). To rotate a **whole
  figure**, apply that to every piece.
- Commit style: end messages with
  `Co-Authored-By: Claude Opus 4.8 <noreply@anthropic.com>`.

## Tasks

1. **Mountain 1** (`nevit_202.json`) — "needs a little clean." Tidy the piece
   placement so the silhouette reads as a clean mountain (close small gaps / align
   the base). Keep it validating; render before/after to confirm it improved.

2. **Bulldozer** (`abstract_2.json`) — "can we rotate it." Rotate the whole figure
   (likely 180°, or whichever orientation reads best) using the 180°-about-center
   recipe above, or a different multiple of 45° via each piece's `orientation`.
   ⚠️ **Depends on Chunk 1a**: Bulldozer is a duplicate of Frame
   (`wiebke_interesting1`). Confirm with Chunk 1 that Bulldozer is being **kept**
   before investing in the rotation — if they delete it instead, skip this.

3. **Goblet** (`nevit_235.json`) — only if Chunk 1's inspection routes it here as a
   **geometry** problem (vs. just a wrong name). If so, fix the placement so it
   reads as intended; otherwise leave it to Chunk 1.

## Done when

Each figure still passes `validate()`, renders correctly, and is mirrored to
`web/public/examples/`. You made **no** edits to `index.json`.
