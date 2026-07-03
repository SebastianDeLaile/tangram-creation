# Chunk 3 — New digit tangrams (construct 7 and 4)

You **create new figure files**. Do the geometry/validation yourself; hand the new
filenames + intended names to **Chunk 1** to add to `examples/index.json` (keeps
index edits in one place). You may add the files to `examples/` and the web mirror.

## Background

Nevit only made digits **1–6**. The library already has 1, 2, 3, 5, 6, and **9**
(built this session as the "6" rotated 180°, `9_number.json`). Missing and
**feasible**: **7** and **4**. Digits **0 and 8 are impossible** as a normal
tangram — 7 solid pieces tile one filled region and can't form a hole — so skip
them.

## Shared context (read first)

- Coordinates are exact ℤ[√2] (`tangram.algebra.Z2`, `a + b√2`). A figure is a
  `Tangram` of 7 `PiecePlacement`s (`piece_type`, `piece_id`, `anchor: Point`,
  `orientation` 0–7 in 45° steps, `flipped`). See `tangram.model`,
  `tangram.pieces`, `tangram.geometry`. Save with `tangram.io.save_tangram`.
- The 7 pieces (each used once, except two large + two small triangles):
  large-tri legs 12√2, medium-tri legs 12, small-tri legs 6√2, square side 6√2,
  parallelogram 12×6. Piece ids: large_triangle 0 & 1, small_triangle 0 & 1,
  medium_triangle 0, square 0, parallelogram 0. Whole set area 576 (a 24×24 square).
- A figure must pass `tangram.validate.validate()`: exactly the 7 pieces with
  correct ids, no overlaps beyond tolerance, and connected (or set
  `allow_disconnected=True` if a digit legitimately has a separated stroke — avoid
  if possible).
- **Study the existing digits for the vocabulary**: load and render (with piece
  edges) `nevit_116` (1), `2_number_117` (2), `3_number_118` (3), `nevit_120` (5),
  `nevit_121` (6). They show how thin strokes and corners are built from these
  pieces.
- Rendering pattern (cairosvg, per piece `fill="black" stroke="white"`): see
  `scripts/find_duplicates.py`.
- Commit style: end messages with
  `Co-Authored-By: Claude Opus 4.8 <noreply@anthropic.com>`.

## Method

Iterative design: place the 7 pieces at chosen anchors/orientations → `validate()`
→ render → adjust → repeat. Tips:
- **7**: a horizontal top bar + a diagonal stroke down to the lower-left. The
  hypotenuse of a large triangle is 12√2·√2 = 24 long — a natural full-height
  diagonal for the slanted stroke; the two large triangles can form the diagonal
  band. Fill the top bar with the medium/small triangles, square, parallelogram.
- **4**: an open wedge at the top-left (diagonal + vertical) meeting a horizontal
  crossbar, plus a vertical stem down the right. Large triangles make the bold
  strokes; smaller pieces close the corners.
- Keep digits ~24 tall so they sit consistently with the existing set.

## Deliverables

- `examples/7_number.json` and `examples/4_number.json` (+ copies in
  `web/public/examples/`), each passing `validate()` and reading clearly as the
  digit when rendered as a plain silhouette.
- Message to **Chunk 1**: the two filenames, `title` "7" / "4", category
  `letters`, `source` e.g. `"constructed"`, `tags` `["constructed"]` — for them to
  append to `index.json`.

## Done when

Both digit files exist, validate, render legibly, and their index entries have been
handed to Chunk 1.
