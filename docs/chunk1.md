# Chunk 1 — Library curation (naming + deduplication)

You own **all edits to `examples/index.json`** this pass. Chunks 2 and 3 touch only
individual figure files and will hand you their index entries, so keep index edits
here to avoid conflicts.

## Shared context (read first)

- `examples/*.json` — one file per figure. `examples/index.json` is the manifest
  (`title`, `category`, `source`, `tags`) and the single source of truth for what
  shows in the app. Categories: `people`, `animals`, `objects`, `geometric`,
  `letters`, `abstract`.
- Every file in `examples/` must be listed in `index.json` and pass
  `tangram.validate.validate()`. After changes run `.venv/bin/pytest tests/ -q`.
- `web/public/examples/` is a **mirror**: after editing `examples/index.json` (or
  deleting a figure file), copy the change there too (`cp examples/index.json
  web/public/examples/index.json`, and delete the mirrored figure file).
- **Sidebar labels** like "Torch 2" number same-titled figures in
  category-then-alphabetical order; the file each maps to is given below.
- To identify a figure, render it. Load with `tangram.io.load_tangram`, rasterize
  with `cairosvg`; render **with piece edges** (each piece `fill="black"
  stroke="white" stroke-width="0.4"`) — the internal structure makes figures far
  easier to recognize than a solid silhouette. See `scripts/identify_tangrams.py`
  and `scripts/find_duplicates.py` for the rendering pattern.
- Commit style: end messages with
  `Co-Authored-By: Claude Opus 4.8 <noreply@anthropic.com>`.

## 1a. Resolve duplicate solutions

`scripts/find_duplicates.py` (run it) reports figure pairs with the **same
silhouette** (IoU ≥ 0.98 under rotation/reflection). For each pair, render both,
keep the better-named / better-placed one, and delete the other: remove its file
from `examples/` **and** `web/public/examples/`, and its `index.json` entry.

| A | B | note |
|---|---|---|
| Cheering (`nevit_233`) | Cheering (`nevit_234`) | identical — keep either |
| Table (`nevit_191`) | Viaduct (`nevit_229`) | pick the better name |
| Bowl (`nevit_103`) | Chalice (`nevit_225`) | user flagged |
| Fox (`nevit_071`) | Fox Running (`nevit_072`) | keep one |
| Mountain (`mountain.json`) | Mountains (`nevit_217`) | user flagged |
| Cat (`cat.json`) | Cat Curled (`nevit_052`) | keep one |
| Frame (`wiebke_interesting1`) | Bulldozer (`abstract_2`) | 0.993 — verify by eye; **see coordination** |

## 1b. Rename / recategorize mislabeled figures

Inspect each, then set the correct `title` and `category` in `index.json`.

| sidebar label | file | user note | action |
|---|---|---|---|
| Arrow 3 | `nevit_227` | "is a hammer" | → **Hammer** / objects |
| House 1 | `nevit_179` | "some kind of bird" | → **Bird** / animals (confirm) |
| House 2 | `nevit_182` | "is a teapot" | → **Teapot** / objects |
| Kite | `nevit_098` | "not a kite" | inspect → rename |
| Stool | `nevit_107` | "is wrong" | inspect → rename |
| Torch 1 | `nevit_115` | "not sure" | inspect → confirm/rename |
| Torch 2 | `nevit_112` | "flare or candle?" | inspect → confirm/rename |
| Tree 1 | `nevit_104` | "not a tree" | inspect → rename |
| Tree 2 | `nevit_236` | "not a tree" | inspect → rename |
| Goblet | `nevit_235` | "looks wrong" | inspect → rename (or hand to Chunk 2 if it's a geometry problem) |
| Candle 2 | `nevit_111` | "delete" | **delete** (file + mirror + index) |

## Coordination with other chunks

- **Bulldozer** (`abstract_2`) is in your dedup table (1a) *and* Chunk 2 wants to
  rotate it. Decide keep-or-delete **first**; only if you keep it does Chunk 2's
  rotation matter.
- **Goblet** (`nevit_235`): if inspection shows it's just mis-named, handle it
  here; if the piece placement is broken, hand it to Chunk 2.
- **Chunk 3** will give you new digit files (`7`, `4`) to append to `index.json`
  (title = the digit, category `letters`). Add them when they land.

## Done when

`pytest` green, `index.json` and `web/public/examples/` in sync, all rows above
resolved.
