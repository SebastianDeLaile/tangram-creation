# tangram-creation

Tangram display generator. Exact-arithmetic geometric model for tangram configurations, SVG rendering, and an interactive Tkinter piece editor.

## Domain

A tangram is 7 pieces (tans) dissected from a square: 2 large triangles, 1 medium triangle, 2 small triangles, 1 square, 1 parallelogram. Pieces are placed by translation + rotation (multiples of 45°) + optional flip (parallelogram only).

## Architecture

- Python package in `src/tangram/`. Coordinates are exact values in ℤ[√2] (`algebra.py::Z2`, backed by `fractions.Fraction`) — never plain floats internally — because 45° rotations involve √2 exactly and this avoids float drift across repeated transforms.
- Module dependency order: `algebra` → `geometry` → `pieces` → `model` → `io` / `render` / `gui`. Keep the core (`algebra`/`geometry`/`pieces`/`model`) free of rendering/UI dependencies so it can be reused (e.g. by a future web backend).
- If a TypeScript web frontend is built later, it's a separate consumer of the JSON config format (`io.py`'s schema) — not a rewrite of the Python core.

## Goals

- Represent tangram piece geometry exactly (coordinates, orientation, piece type)
- Accept a full 7-piece configuration as input (JSON, see README for schema)
- Render a configuration to SVG
- Provide an interactive editor for live piece placement (drag/rotate/flip)

## Environment notes

- Tkinter (used by `gui.py`) requires `python-tk@<version>` via Homebrew on macOS — not bundled with Homebrew's Python by default.

## Roadmap

- Editor: snap-to-piece edges/vertices (not just integer grid), overlap/coverage feedback, a piece palette to start from a blank canvas, in-GUI SVG export.
- Eventually deploy a web version to the user's own domain. Planned path: TypeScript web frontend consuming the same JSON config schema (`io.py`), not a rewrite of the Python core — see Architecture above. No hosting target or stack chosen yet.

## See also

README.md for full project description, geometry notes, module layout, and usage examples.
