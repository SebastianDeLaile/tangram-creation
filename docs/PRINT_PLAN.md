# Print & PDF Plan

Goal: let people generate **print-ready puzzle cards** from the figure library —
silhouette + label on one side, colored solution on the other — suitable for
home printing or upload to a print shop (e.g. Officeworks). Plus an
auto-computed **difficulty** score so cards and packs can be graded.

This builds on what already exists:

- The web app already renders a **Silhouette panel** (solid, seamless, sharp
  corners) next to the **Solution panel** (colored, editable) — `web/src/main.ts`.
- Figures already carry metadata (`title`, `category`, `source`, `tags`) in
  `examples/index.json`. A `difficulty` field is added by this plan (Part 3).
- The Python core has an exact geometry model and a silhouette/convexity
  extractor (`src/tangram/boundary.py`) we reuse for scoring.
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
- **Print root** — a container (hidden on screen, shown only under
  `@media print`) that lays out cards. Reuse the exact SVG both panels already
  produce; no new geometry code.
- **Card = two faces:**
  - **Front:** silhouette (solid black on white — cheapest, highest contrast),
    the figure `title`, a **difficulty** indicator (★★★☆☆), and the
    `category`/theme label.
  - **Back:** the colored solution.
- **Duplex alignment:** the back face must be **mirrored horizontally** so that,
  printed double-sided (flip on long edge) and cut, the solution sits behind its
  own silhouette. This is the single most important print detail.
- **Layout:** N-up on A4 — start with 4 cards/page (A6) — with faint **cut
  lines / crop marks** and a thin card border so they can be guillotined.
- **Page setup:** `@page { size: A4; margin: 0 }` and CSS respecting the
  1:√2 proportions the canvases already use.
- **Selection:** v0 prints the currently-open figure. A later pass adds
  multi-select ("add to print sheet").

Acceptance for v0: open a figure → Print → Save as PDF → the PDF has a silhouette
face and a mirrored solution face that line up when printed double-sided.

### v1: Real client-side PDF library  ✅ implemented

`web/src/pdf.ts` replaces `window.print()` with programmatic PDF via `jsPDF` +
`svg2pdf.js` (lazy-loaded on click so it stays out of the initial bundle):

- **A5 pages**, each auto-oriented **portrait or landscape** to fit the tangram
  — sized for lamination and ring-binder storage rather than A4 cards.
- **Back-side mirroring** in the SVG transform for duplex registration.
- **Optional binding gutter** (`gutter` toggle): a blank hole-punch strip on the
  left of the front and, mirrored, the right of the back, so punched holes align
  through the flipped sheet. Off by default-able via the sidebar checkbox.
- **Card outline + corner crop marks** for trimming/laminating.
- **Difficulty dots** drawn as jsPDF vector circles (PDF core fonts lack ★).
- **Batch export:** "Download all shown" emits every currently-listed figure as
  duplex cards in one file (front/back interleaved for auto-duplex printing).

Not yet done from the original v1 wish-list: a dedicated print-scale calibration
square (crop marks + known A5 size cover scale verification for now) and a
multi-**select** tray (batch currently follows the sidebar filter instead).

### v2: Themed packs & worksheets

- **Category packs:** one-click PDF of all "Animals" / "Letters" / etc.
- **Difficulty packs:** "Easy pack", "Hard pack" once scoring lands.
- **Solve-on-top worksheet mode:** silhouette printed at *true puzzle scale* so
  physical tans can be laid on top. Needs a real-scale render mode — today all
  figures scale-to-fit their box (a known README tradeoff), so this is a
  deliberate extra rather than free.
- **QR code per card** linking to the figure in the deployed web editor.

## Part 2 — Whole-library booklet (Python)

A batch generator that renders the entire library into one polished,
print-ready **puzzle book** PDF — a shareable/sellable artifact, runnable in CI.

- New module alongside the SVG renderer, e.g. `src/tangram/pdf.py`, using
  `reportlab` or `cairosvg` (reuse `render.render_svg`).
- Structure: cover → puzzle pages (silhouettes, grouped by category/difficulty)
  → answer-key section (solutions contact sheet) at the back.
- CLI entry point to regenerate the book from `examples/` + `index.json`.
- Optional: wire into CI to publish the latest book as a build artifact.

## Part 3 — Auto-computed difficulty (Python scorer)  ✅ implemented

Difficulty is **derived from the exact model**, not hand-labeled. Real tangram
difficulty correlates with computable properties:

- **Silhouette convexity** — convex/compact shapes are *harder* (fewer boundary
  cues). `boundary.py::is_convex_tangram`.
- **Compactness** — the 7 pieces always total area 576, so fill ratio =
  576 ÷ bounding-box area. Compact = harder.
- **Silhouette perimeter** — shorter outline = fewer notches/cues = harder.
- **Orientation variety** — distinct `orientation` values used; parallelogram
  `flipped`. More variety = subtler placements.

Delivered as:

- `src/tangram/difficulty.py` — `score(tangram)` returns the sub-metrics plus a
  combined raw score; `stars(raw)` buckets to 1–5.
- `scripts/score_difficulty.py` — scores every figure and writes a `difficulty`
  field (1–5) into each `examples/index.json` entry, then reminds you to
  re-copy `examples/` → `web/public/examples/` (per CLAUDE.md).
- The web sidebar reads `index.json`, so difficulty then drives **sort/filter**
  in the UI and appears on the printed card — no schema plumbing beyond the
  new field.

Scoring is a heuristic; the sub-metrics are exposed so weighting can be tuned
and spot-checked against known easy/hard figures.

---

## Suggested order of work

1. ~~**Difficulty scorer**~~ (done — unblocks card + sidebar labels).
2. ~~**Print-CSS v0**~~ (superseded by the vector PDF in step 4).
3. ~~**Sidebar difficulty sort/filter**~~ (done — star ratings + A–Z/Difficulty toggle).
4. ~~**PDF library v1**~~ (done — A5 duplex cards, auto orientation, optional gutter).
5. **Python booklet** + optional CI artifact.
6. **Packs, worksheet mode, QR codes** (v2 polish).

## Open questions

- ~~Card size / orientation~~ — resolved: **A5**, auto portrait/landscape per
  tangram, optional binding gutter for hole-punching.
- Whether the booklet should be a product (cover art, attribution page) or an
  internal artifact.
- Difficulty weighting: which metrics matter most, calibrated against a few
  hand-picked easy/hard reference figures.
