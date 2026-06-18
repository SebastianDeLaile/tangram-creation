# tangram-creation

Tangram display generator. Exact-arithmetic geometric model for tangram configurations, SVG rendering, and two interactive piece editors: a Tkinter desktop app and a TypeScript/Vite browser app.

## Domain

A tangram is 7 pieces (tans) dissected from a square: 2 large triangles, 1 medium triangle, 2 small triangles, 1 square, 1 parallelogram. Pieces are placed by translation + rotation (multiples of 45°) + optional flip (parallelogram only).

## Architecture

- Python package in `src/tangram/`. Coordinates are exact values in ℤ[√2] (`algebra.py::Z2`, backed by `fractions.Fraction`) — never plain floats internally — because 45° rotations involve √2 exactly and this avoids float drift across repeated transforms.
- Module dependency order: `algebra` → `geometry` → `pieces` → `model` → `io` / `render` / `gui`. Keep the core (`algebra`/`geometry`/`pieces`/`model`) free of rendering/UI dependencies so it can be reused (e.g. by a future web backend).
- `web/` (TypeScript + Vite) is a parallel implementation of the same exact-arithmetic model (`web/src/algebra.ts` etc., using a small `Fraction` class since JS has no built-in rational type), not a wrapper around the Python code. Both sides read/write the identical JSON schema (`io.py` / `web/src/io.ts`) — that schema is the integration seam, not a shared runtime. When the geometry model changes, update both implementations and keep their behavior identical (e.g. rotation must produce bit-for-bit the same exact values — verified once via a manual cross-check, not an automated test yet).
- `web/public/examples/*.json` (including `index.json`) is a copy of the top-level `examples/`, served statically by Vite. If the canonical examples change, re-copy them (`rm web/public/examples/*.json && cp examples/*.json web/public/examples/`).
- The web sidebar (`web/src/main.ts`) reads `examples/index.json` at runtime to build its categorized shape list — adding a figure to `examples/` + `index.json` and re-copying is enough for it to show up, no code change needed.
- `src/tangram/validate.py` checks piece counts and non-overlap for a `Tangram`; every file in `examples/` must pass it (enforced by `tests/test_validate.py`). The web app doesn't currently run this check client-side.

## Goals

- Represent tangram piece geometry exactly (coordinates, orientation, piece type)
- Accept a full 7-piece configuration as input (JSON, see README for schema)
- Render a configuration to SVG
- Provide an interactive editor for live piece placement (drag/rotate/flip)
- Web editor extras: shapes grouped by category, theme presets + per-piece-type color pickers, fill/outline toggle, solution/silhouette toggle

## Environment notes

- Tkinter (used by `gui.py`) requires `python-tk@<version>` via Homebrew on macOS — not bundled with Homebrew's Python by default.
- `web/` needs Node/npm (`cd web && npm install && npm run dev`). Currently runs locally only, no public deployment.

## Roadmap

- Editor (both Python and web): snap-to-piece edges/vertices (not just integer grid), overlap/coverage feedback, a piece palette to start from a blank canvas, in-GUI SVG export.
- Eventually deploy the web app to the user's own domain. No domain name, hosting provider, or timeline chosen yet — ask for specifics when this becomes concrete.

## See also

README.md for full project description, geometry notes, module layout, and usage examples.
