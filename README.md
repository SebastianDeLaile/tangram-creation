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

Four configurations are provided in `examples/`, sourced from the open-source [TangramGenerator](https://github.com/Wiebke/TangramGenerator) project and converted to this exact format:

| File | Silhouette |
|---|---|
| `square.json` | The 7 pieces assembled into the original square |
| `cat.json` | Sitting cat |
| `bird.json` | Bird in flight |
| `swan.json` | Swan |

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

## Project structure

```
tangram-creation/
├── README.md
├── pyproject.toml
├── src/tangram/        # the package (see Module layout above)
├── tests/              # pytest suite
└── examples/           # example configurations
```
