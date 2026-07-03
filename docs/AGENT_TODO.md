# Library cleanup — agent handoff index

Review feedback from browsing the deployed library, split into chunks that can be
handed to separate agents. Each chunk file is self-contained (includes the shared
context an agent needs cold).

- **[chunk1.md](chunk1.md)** — Library curation. Owns all `examples/index.json`
  edits: resolve 7 duplicate-solution pairs, delete Candle 2, rename/recategorize
  10 mislabeled figures.
- **[chunk2.md](chunk2.md)** — Geometry fixes (individual figure files, no
  `index.json`): clean Mountain 1, rotate Bulldozer, fix Goblet if geometric.
- **[chunk3.md](chunk3.md)** — New digit tangrams: construct 7 and 4.

## Chunking rationale

`examples/index.json` (+ its `web/public/examples/` mirror) is edited by every
rename/delete/dedup, so it's the one contention point. **Chunk 1 is the sole
`index.json` editor**; Chunks 2 and 3 touch only individual figure files and hand
their index entries to Chunk 1 — so 2 and 3 can run in parallel with 1.

Two cross-links to settle before parallelizing (both noted in the chunk files):
- **Bulldozer** (`abstract_2`) — dedup candidate in Chunk 1a *and* rotate target in
  Chunk 2. Decide keep/delete first.
- **Goblet** (`nevit_235`) — wrong name (Chunk 1) vs. possible broken geometry
  (Chunk 2). Inspect first to route.

## Already done this session (do NOT redo)

- Deleted: Heron 1 (`nevit_133`), Horse 3 (`nevit_035`), 5 sparse "Abstract"
  figures, duplicate square (`nevit_243`).
- Renamed: Horse 1→Dog (`nevit_060`), Rabbit 4→Boat (`nevit_090`), Rabbit 3→Fox
  (`nevit_083`), Rabbit 1→Bird (`nevit_061`, tentative).
- Moose (`nevit_245`): tail moved in, back straightened, renamed from "Abstract".
- Base square featured at top of sidebar.
- Built `scripts/find_duplicates.py` (silhouette duplicate matcher) and digit
  **9** (`9_number.json`).
