#!/usr/bin/env python3
"""Score every figure's difficulty and write it into examples/index.json.

Difficulty is auto-derived from the exact geometry model (see
tangram.difficulty) -- no hand-labeling. Each entry in index.json gains a
``difficulty`` field (1-5 stars).

Usage:
    PYTHONPATH=src python3 scripts/score_difficulty.py            # write index.json
    PYTHONPATH=src python3 scripts/score_difficulty.py --stats    # print, don't write
    PYTHONPATH=src python3 scripts/score_difficulty.py --dry-run  # alias for --stats

After writing, re-copy examples/ -> web/public/examples/ so the web app picks
up the new field (per CLAUDE.md):

    rm web/public/examples/*.json && cp examples/*.json web/public/examples/
"""
from __future__ import annotations

import argparse
import json
import sys
from collections import Counter
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(REPO_ROOT / "src"))

from tangram.difficulty import score  # noqa: E402
from tangram.io import load_tangram  # noqa: E402

EXAMPLES_DIR = REPO_ROOT / "examples"
INDEX_PATH = EXAMPLES_DIR / "index.json"


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "--stats",
        "--dry-run",
        action="store_true",
        dest="stats",
        help="print the score for every figure and the star distribution, without writing",
    )
    args = parser.parse_args()

    index = json.loads(INDEX_PATH.read_text())
    figures = index["figures"]

    distribution: Counter[int] = Counter()
    rows = []
    for entry in figures:
        path = EXAMPLES_DIR / entry["file"]
        if not path.exists():
            print(f"  WARNING: missing figure file {entry['file']}", file=sys.stderr)
            continue
        result = score(load_tangram(path))
        entry["difficulty"] = result.stars
        distribution[result.stars] += 1
        rows.append((result.raw, result.stars, entry["file"], result.convex))

    if args.stats:
        for raw, stars, file, convex in sorted(rows):
            flag = " convex" if convex else ""
            print(f"  {stars}★  raw={raw:.3f}  {file}{flag}")
    else:
        INDEX_PATH.write_text(json.dumps(index, indent=2) + "\n")
        print(f"Wrote difficulty for {len(rows)} figures to {INDEX_PATH.relative_to(REPO_ROOT)}")
        print(
            "Remember to re-copy examples -> web/public/examples so the web app "
            "sees the new field (see CLAUDE.md)."
        )

    print("Star distribution: " + "  ".join(
        f"{s}★={distribution[s]}" for s in range(1, 6)
    ))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
