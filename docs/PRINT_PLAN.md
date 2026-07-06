# Print & PDF Plan

Goal: let people generate **print-ready puzzle cards** from the figure library —
silhouette + label on one side, colored solution on the other — suitable for
home printing or upload to a print shop (e.g. Officeworks). Plus an
auto-computed **difficulty** score so cards and packs can be graded.

This builds on what already exists:

- The web app already renders a **Silhouette panel** (solid, seamless, sharp
  corners) next to the **Solution panel** (colored, editable) — `web/src/main.ts`.
- Figures already carry metadata (`title`, `category`, `source`, `tags`) in
  `examples/index.json`. **No `difficulty` field yet** — this plan adds one.
- The Python core has an exact geometry model and a silhouette/convexity
  extractor (`src/tangram/boundary.py`) we can reuse for scoring.
- The web app is a **static GitHub Pages deploy** (`.github/workflows/deploy.yml`)
  with **no backend** — so any in-browser export must be client-side.

## Decisions locked in

- **First PDF export = Print-CSS v0** (`@media print` stylesheet +
  `window.print()` → "Save as PDF"). Near-zero dependencies, works on the
  static deploy, proves the card layout. Upgrade to a real PDF library later.
- **Build the difficulty scorer** — auto-derive difficulty from the exact model
  and write it into `index.json`.

---

## Part 1 — Print-ready cards (web)

### v0: Print stylesheet + `window.print()`

The cheapest thing that produces a real, uploadable PDF: a dedicated print
layout the browser turns into a PDF via "Save as PDF" in the print dialog.

- **New "Print" button** in the sidebar (`web/src/main.ts`), next to "Download
  JSON".
- **Print view / print root** — a container (hidden on screen, shown only under
  `@media print`) that lays out cards. Reuse the exact SVG both panels already
  produce; no new geometry code.
- **Card = two faces:**
  - **Front:** silhouette (solid black on white — cheapest, highest contrast),
    the figure `title`, a **difficulty** indicator (e.g. ★★★☆☆), and the
    `category`/theme label.
  - **Back:** the colored solution.
- **Duplex alignment:** the back face must be **mirrored horizontally** so that,
  printed double-sided (flip on long edge) and cut, the solution sits behind its
  own silhouette. This is the single most important print detail.
- **Layout:** N-up on A4 — start with 4 cards/page (A6) — with faint **cut
  lines / crop marks** and a thin card border so they can be guillotined.
- **Page setup:** `@page { size: A4; margin: 0 }` and CSS that respects the
  1:√2 proportions the canvases already use.
- **Selection:** v0 can print the currently-open figure (front+back on one
  sheet, or a test 4-up). A later pass adds multi-select ("add to print sheet").

Acceptance for v0: open a figure → Print → Save as PDF → the PDF has a silhouette
face and a mirrored solution face that line up when printed double-sided.

### v1: Real client-side PDF library

Once the layout is proven, replace `window.print()` with programmatic PDF
generation for pixel control, reliable duplex, and multi-card sheets:

- Library options: `jsPDF` + `svg2pdf.js`, or `pdf-lib`. Feed the existing
  per-panel SVG straight in.
- **True A-series page sizes** with margins/bleed.
- **Crop marks + cut border** drawn into the PDF.
- **Back-side mirroring** handled in the transform.
- **Print calibration square** on the sheet ("this square should measure X cm")
  so users verify printer scale before cutting.
- **Multi-select tray:** pick many figures → one multi-page, N-up PDF.

### v2: Themed packs & worksheets

- **Category packs:** one-click PDF of all "Animals" / "Letters" / etc. (figures
  already carry `category`).
- **Difficulty packs:** "Easy pack", "Hard pack" once scoring lands.
- **Solve-on-top worksheet mode:** silhouette printed at *true puzzle scale* so
  physical tans can be laid on top. Needs a real-scale render mode — today all
  figures scale-to-fit their box (a known tradeoff noted in the README), so this
  is a deliberate extra rather than free.
- **QR code per card** linking to the figure in the deployed web editor.

## Part 2 — Whole-library booklet (Python)

A batch generator that renders the entire library into one polished,
print-ready **puzzle book** PDF — good as a shareable/sellable artifact and
runnable in CI.

- New module alongside the SVG renderer, e.g. `src/tangram/pdf.py`, using
  `reportlab` or `cairosvg` (reuse `render.render_svg`).
- Structure: cover → puzzle pages (silhouettes, grouped by category/difficulty)
  → answer-key section (solutions contact sheet) at the back.
- CLI entry point to regenerate the book from `examples/` + `index.json`.
- Optional: wire into CI to publish the latest book as a build artifact.

## Part 3 — Auto-computed difficulty (Python scorer)

Difficulty should be **derived from the exact model**, not hand-labeled across
hundreds of figures. Real tangram difficulty correlates with computable
properties, most of which we can already measure:

- **Silhouette convexity** — convex/compact shapes are *harder* (fewer boundary
  cues). `boundary.py::is_convex_tangram` already answers this.
- **Hidden internal seams** — ratio of piece edges that fall in the interior vs
  on the outer silhouette. More hidden seams = harder to infer placements.
  Derivable from `boundary.boundary_edges` vs all piece edges.
- **Orientation variety** — count of distinct `orientation` values used across
  pieces; whether the parallelogram is `flipped`.
- **Compactness** — bounding-box fill ratio (silhouette area ÷ bbox area);
  compact = harder, spindly = easier.

### Deliverable

- A script (same pattern as the existing importers under `scripts/`) that:
  1. Loads every figure, computes the metrics above,
  2. Combines them into a **1–5 star** score,
  3. Writes a `difficulty` field into each entry in `examples/index.json`.
- Re-copy `examples/` → `web/public/examples/` (per CLAUDE.md, the web copy is
  kept in sync).
- The web sidebar reads `index.json`, so difficulty can then drive **sort/filter
  in the UI** and appear on the printed card — no schema plumbing beyond the new
  field.

Scoring is a heuristic; expose the sub-metrics so the weighting can be tuned and
spot-checked against a few known easy/hard figures.

---

## Suggested order of work

1. **Difficulty scorer** (Python, self-contained, unblocks card + sidebar labels).
2. **Print-CSS v0** (web) — silhouette front / mirrored solution back, 4-up A4,
   cut marks, Print button.
3. **Sidebar difficulty sort/filter** (small win, reuses the new field).
4. **PDF library v1** (web) — real duplex, multi-select, calibration square.
5. **Python booklet** + optional CI artifact.
6. **Packs, worksheet mode, QR codes** (v2 polish).

## Open questions

- Card size preference (A6 4-up vs A5 2-up) and default page size (A4 assumed).
- Whether the booklet should be a product (cover art, attribution page — sources
  are already tracked per figure) or just an internal artifact.
- Difficulty weighting: which metrics matter most, calibrated against a few
  hand-picked easy/hard reference figures.
