# tangram-creation

A tangram display generator: an exact-arithmetic geometric model for tangram configurations, an SVG renderer, and an interactive piece editor.

## What is a tangram?

A tangram is a classic Chinese dissection puzzle consisting of seven flat shapes (called *tans*) cut from a square:

| Piece | Count | Description |
|---|---|---|
| Large right triangle | 2 | Quarter the area of the original square each |
| Medium right triangle | 1 | Eighth the area |
| Small right triangle | 2 | Sixteenth the area each |
| Square | 1 | Eighth the area |
| Parallelogram | 1 | Eighth the area |

All seven pieces together tile the original square exactly, with no overlaps or gaps. The same seven pieces can also be rearranged into hundreds of other *silhouettes* (animals, people, objects) — that's the actual puzzle.

## What this project does

1. **Geometric model** (`src/tangram/`) — exact representation of each piece's position, orientation, and shape.
2. **SVG renderer** — turns a configuration into an image.
3. **Interactive editor** — a Tkinter window for dragging, rotating, and flipping pieces live.

A configuration is any free placement of all seven pieces without overlap — not restricted to the original square.

## Geometry: exact arithmetic in ℤ[√2]

Tangram pieces rotate in multiples of 45°, and cos(45°) = sin(45°) = √2⁄2. That means every piece vertex, at any rotation, is exactly representable as *a* + *b*√2 for rational *a*, *b* — the ring **ℤ[√2]**. This project stores coordinates that way (`src/tangram/algebra.py::Z2`, backed by `fractions.Fraction`) instead of as floats, so dragging, rotating, and re-rotating a piece never accumulates floating-point drift. Floats only appear at the final step, when converting to pixels for display.

The full assembled square has side length 24 in this coordinate system (chosen so canonical piece sizes are clean integers/√2-multiples).

### Canonical piece sizes (at orientation 0)

| Piece | Leg length | Anchor |
|---|---|---|
| Large triangle | 12√2 ≈ 16.97 | right-angle vertex |
| Medium triangle | 12 | right-angle vertex |
| Small triangle | 6√2 ≈ 8.49 | right-angle vertex |
| Square | side 6√2 | one corner |
| Parallelogram | 12 × 6 (base × offset) | one corner |

## Module layout

```
src/tangram/
├── algebra.py    # Z2: exact a + b*sqrt(2) arithmetic
├── geometry.py   # Point: 2D point over Z2, with exact 45-degree rotation
├── pieces.py     # PieceType enum, canonical piece shapes, colors
├── model.py      # PiecePlacement (one piece's placement), Tangram (all 7)
├── io.py         # load/save Tangram <-> JSON, preserving exact coordinates
├── render.py     # Tangram -> SVG
└── gui.py        # interactive Tkinter piece editor
```

Each module only depends on the ones above it in this list — `algebra` has no project dependencies, `render` and `gui` depend on everything below them. This keeps the core geometry usable on its own (e.g. from a future web backend) without pulling in rendering or UI code.

## Configuration format

Each configuration is a JSON object with exact, lossless coordinates:

```json
{
  "name": "square",
  "description": "The 7 pieces assembled into the original 4x4 square",
  "pieces": [
    {
      "piece": "large_triangle",
      "id": 0,
      "anchor": { "x": [12, 0], "y": [12, 0] },
      "orientation": 1,
      "flipped": false
    }
  ]
}
```

Fields:
- `piece` — `large_triangle`, `medium_triangle`, `small_triangle`, `square`, `parallelogram`
- `id` — `0` or `1`, to distinguish the two copies of pieces that appear twice
- `anchor.x` / `anchor.y` — `[a, b]` meaning the exact value *a* + *b*√2 (each an integer, or a string like `"3/2"` for a non-integer fraction)
- `orientation` — rotation applied counter-clockwise from canonical position, in steps of 45°: `0`–`7`
- `flipped` — `true` for the mirrored orientation of the parallelogram (meaningless for other piece types)

Polygon vertices aren't stored — they're derived from `anchor` + `orientation` + `flipped` via `PiecePlacement.vertices()`.

## Examples

`examples/` holds the figure library: 12 configurations so far, mostly sourced
from the open-source [TangramGenerator](https://github.com/Wiebke/TangramGenerator)
project and converted to this exact format (see `scripts/import_tangram_generator.py`).
`examples/index.json` is the manifest — every file is listed there with a
category (`geometric`, `animals`, `objects`, `letters`, `abstract`) and source.
The sourcing strategy, category taxonomy, and roadmap to 100+ figures are
documented in [`docs/LIBRARY_PLAN.md`](docs/LIBRARY_PLAN.md).

Every figure in `examples/` is required to pass `tangram.validate.validate()`
(correct piece counts, no overlaps) — enforced by `tests/test_validate.py`.

## Usage

```bash
python3 -m venv .venv
.venv/bin/pip install -e .

# Render a configuration to SVG
.venv/bin/python3 -c "
from tangram.io import load_tangram
from tangram.render import save_svg
save_svg(load_tangram('examples/cat.json'), 'cat.svg')
"

# Open the interactive editor
.venv/bin/python3 -m tangram.gui examples/cat.json
```

The editor: click a piece to select it, drag to translate (snapped to the integer grid), `R` to rotate 45°, `F` to flip the parallelogram, `S` to save back to the loaded file.

The interactive editor needs Tkinter. On macOS with Homebrew Python, install it with:

```bash
brew install python-tk@3.14   # match your Python version
```

## Web frontend

`web/` is a TypeScript + Vite port of the same editor, runnable in a browser. It's a separate implementation of the geometry model (`web/src/algebra.ts`, `geometry.ts`, `pieces.ts`, `model.ts`) that consumes the exact same JSON config schema as the Python package — not a wrapper around the Python code. The Python package stays the source of truth for configs; the web app is just another reader/writer of the same format.

```bash
cd web
npm install
npm run dev
```

Then open the printed `localhost` URL. Same piece interactions as the Tkinter editor: click to select, drag to translate (grid-snapped), `R` to rotate, `F` to flip. Around that:

- **Collapsible left sidebar** — shapes grouped by category (reads `examples/index.json` directly, so any figure added there shows up automatically), a theme picker, a color swatch per piece type, fill/outline toggle, corner rounding slider, and a "Download JSON" button (browsers can't write back to a local file directly, so this downloads the edited config instead of overwriting it in place). Collapse it with the `«`/`»` button at the top to give the canvases more room.
- **Themes** (`web/src/themes.ts`) — grouped palettes that set all 5 piece colors at once; individual color pickers can still override on top.
  - *Classics*: `classic`, `pastel`, `mono`
  - *Designer*: `bauhaus` (De Stijl primaries), `nord` (Arctic Ice Studio's aurora accents), `dracula`, `solarized` (Ethan Schoonover), `memphis` (1980s Memphis Group), `terracotta` (muted earth tones)
- **Solution + Silhouette panels, side by side** — the Solution panel is the normal colored, editable view. Next to it, a read-only Silhouette panel always shows the same configuration as a single solid color with no internal seams (the puzzle silhouette you'd be asked to solve from). It's intentionally independent of the Solution panel's fill/outline toggle and corner rounding — always solid-filled with sharp corners, only its color is customizable.
- **Fill / Outline** (Solution panel only) — solid pieces, or bold 4px rounded-join strokes with no fill.
- **Corner rounding** (Solution panel only) — a slider (0-100%) that rounds every piece's corners. Implemented as a quadratic-curve cut at each vertex (`web/src/roundedPath.ts::roundedPolygonPath`), capped at half the shorter adjacent edge so corners never overlap — at 100% a square becomes a circle and triangles become lens shapes, predictably. Pieces render as `<path>` elements (not `<polygon>`) to support this.
- **Stable canvas size** — both panels are always drawn inside a fixed box matching A-series paper proportions (1 : √2, e.g. A5), landscape or portrait depending on whichever a given figure's own bounding box fits better. The box itself only ever takes one of those two fixed pixel sizes, and each shape is scaled to fit and centered inside it — so switching between figures of very different sizes doesn't make the page jump around. Comes at the cost of true relative scale between figures (a single piece and a sprawling 7-piece figure both get scaled to fill the same box).

This currently runs locally only — no public deployment yet.

## Project structure

```
tangram-creation/
├── README.md
├── pyproject.toml
├── src/tangram/        # the Python package (see Module layout above)
├── tests/              # pytest suite
├── examples/           # figure library + index.json manifest (see docs/LIBRARY_PLAN.md)
├── scripts/            # one-off/reusable importers that feed examples/
├── docs/               # LIBRARY_PLAN.md: sourcing strategy and roadmap
└── web/                # TypeScript/Vite browser editor (mirrors src/tangram/)
    ├── src/             # algebra.ts, geometry.ts, pieces.ts, model.ts, io.ts, main.ts
    └── public/examples/ # copy of ../examples/*.json, served statically
```
