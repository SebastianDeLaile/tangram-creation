# Library cleanup TODO (for handoff to agents)

Review feedback gathered while browsing the deployed library. Sidebar labels
(e.g. "Torch 2") come from the web app, which numbers same-named figures in
category-then-alphabetical order; the file each maps to is given below so agents
don't have to re-derive it.

## How the library is structured (context for any agent)

- `examples/*.json` — one file per figure. `examples/index.json` is the manifest
  (title, category, source, tags) and is the **single source of truth** for what
  shows in the app.
- Every file in `examples/` **must** be listed in `index.json` and **must** pass
  `tangram.validate.validate()` — enforced by `tests/test_validate.py` (run
  `.venv/bin/pytest tests/ -q`).
- `web/public/examples/` is a **mirror**; after any change to `examples/`, copy the
  changed files (and `index.json`) there too, or the site won't update.
- Renders for visual review: load a figure and rasterize its silhouette with
  `cairosvg` (see `scripts/find_duplicates.py` / `scripts/identify_tangrams.py`
  for the pattern). Rendering **with piece edges** (white stroke) makes figures
  much easier to identify than a solid silhouette.

## Already done this session (do NOT redo)

- Deleted: Heron 1 (`nevit_133`), Horse 3 (`nevit_035`), 5 sparse "Abstract"
  figures, duplicate square (`nevit_243`).
- Renamed: Horse 1→Dog (`nevit_060`), Rabbit 4→Boat (`nevit_090`),
  Rabbit 3→Fox (`nevit_083`), Rabbit 1→Bird (`nevit_061`, tentative).
- Moose (`nevit_245`): tail moved in, back straightened, renamed from "Abstract".
- Base square featured at top of sidebar.
- Built `scripts/find_duplicates.py` (silhouette duplicate matcher).
- Built digit **9** (`9_number.json`, = the "6" rotated 180°).

---

# CHUNK 1 — Library curation  (owns `examples/index.json`)

One agent should own **all** `index.json` edits to avoid conflicts. Two sub-tasks:

## 1a. Resolve duplicate solutions (from `scripts/find_duplicates.py`, IoU≥0.98)

Each pair is the **same silhouette**. Keep the better-named / better-placed one,
delete the other (remove its file from `examples/` and `web/public/examples/` and
its `index.json` entry). Verify visually first.

| A | B | suggested keep |
|---|---|---|
| Cheering (`nevit_233`) | Cheering (`nevit_234`) | either (identical) |
| Table (`nevit_191`) | Viaduct (`nevit_229`) | pick the better name |
| Bowl (`nevit_103`) | Chalice (`nevit_225`) | user flagged — keep one |
| Fox (`nevit_071`) | Fox Running (`nevit_072`) | keep one |
| Mountain (`mountain.json`) | Mountains (`nevit_217`) | user flagged — keep one |
| Cat (`cat.json`) | Cat Curled (`nevit_052`) | keep one |
| Frame (`wiebke_interesting1`) | Bulldozer (`abstract_2`) | 0.993 — verify; see Chunk 2 note |

## 1b. Rename / recategorize mislabeled figures (inspect each, then set title+category)

| sidebar label | file | user note | action |
|---|---|---|---|
| Arrow 3 | `nevit_227` | "is a hammer" | → **Hammer** / objects |
| House 1 | `nevit_179` | "some kind of bird" | → **Bird** / animals (confirm species) |
| House 2 | `nevit_182` | "is a teapot" | → **Teapot** / objects |
| Kite | `nevit_098` | "not a kite" | inspect → rename |
| Stool | `nevit_107` | "is wrong" | inspect → rename |
| Torch 1 | `nevit_115` | "not sure" | inspect → confirm/rename |
| Torch 2 | `nevit_112` | "flare or candle?" | inspect → confirm/rename |
| Tree 1 | `nevit_104` | "not a tree" | inspect → rename |
| Tree 2 | `nevit_236` | "not a tree" | inspect → rename |
| Goblet | `nevit_235` | "looks wrong" | inspect → rename or hand to Chunk 2 if geometry |
| Candle 2 | `nevit_111` | "delete" | **delete** (file + index) |

---

# CHUNK 2 — Geometry fixes  (individual figure `.json` files, do NOT touch `index.json`)

Edit piece placements in the exact ℤ[√2] model; keep `validate()` passing; mirror
to `web/public/examples/`. Pattern for exact edits: translate/rotate a piece via
`Z2`/`Point` arithmetic (see the Moose cleanup in git log `505fe3c`).

- **Mountain 1** (`nevit_202.json`) — "needs a little clean": tidy piece placement
  so the silhouette reads as a clean mountain.
- **Bulldozer** (`abstract_2.json`) — "can we rotate": rotate the figure.
  ⚠️ **Depends on Chunk 1a**: Bulldozer is a duplicate of Frame — decide keep/delete
  before spending effort rotating it.
- **Goblet** (`nevit_235.json`) — only if inspection (Chunk 1b) finds it's a
  geometry problem rather than just a wrong name.

---

# CHUNK 3 — New digit tangrams  (adds new files)

Context: Nevit only made digits **1–6**. We have 1,2,3,5,6 and just added **9**.
Missing that are feasible: **7** and **4** (0 and 8 are impossible as a normal
tangram — 7 solid pieces can't form a hole).

- Construct **digit 7** and **digit 4** by hand: place the 7 pieces on the grid,
  `validate()`, render, iterate. Piece sizes: large-tri legs 12√2, medium-tri legs
  12, small-tri legs 6√2, square side 6√2, parallelogram 12×6. Full set area 576.
- Save each as `examples/N_number.json` + web mirror.
- Hand the new filenames + intended title ("7"/"4", category `letters`) to Chunk 1
  to append to `index.json` (keeps index edits in one place).

---

# Why it's chunked this way

`index.json` (+ its web mirror) is edited by every rename/delete/dedup, so it's the
one real contention point. The split keeps **Chunk 1 as the sole `index.json`
editor**; Chunks 2 and 3 touch only individual figure files and hand their index
entries to Chunk 1. That lets 2 and 3 run in parallel with 1. The one cross-link to
watch is the **Bulldozer** (dup-resolution in 1a vs rotate in 2) and the **Goblet**
(name in 1b vs possible geometry in 2) — resolve those two before parallelizing.
