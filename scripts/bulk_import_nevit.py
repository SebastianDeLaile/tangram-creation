"""Batch-convert downloaded Nevit Dilmen SVGs into examples/, categorized.

Expects three JSON files (produced by the one-off Commons API fetch -- see
docs/LIBRARY_PLAN.md for the queries used) and a directory of downloaded SVGs:
  - a meta file mapping "File:Tangram NNN Nevit.svg" -> {url, categories}
  - a categorized file mapping the same titles -> {bucket, content_tags},
    where bucket is one of this project's categories and content_tags are
    human-readable hints (e.g. "Horse riding") pulled from Commons categories
  - the directory of downloaded "Tangram_NNN_Nevit.svg" files

Usage:
    python3 scripts/bulk_import_nevit.py /tmp/nevit_meta.json /tmp/nevit_categorized.json /tmp/nevit_svgs
"""
from __future__ import annotations

import json
import re
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent / "src"))
sys.path.insert(0, str(Path(__file__).resolve().parent))

from import_nevit_svg import build_tangram, extract_polygons  # noqa: E402
from tangram.io import save_tangram  # noqa: E402
from tangram.validate import validate  # noqa: E402

EXAMPLES_DIR = Path(__file__).resolve().parent.parent / "examples"


def slugify(text: str) -> str:
    text = re.sub(r"[^a-zA-Z0-9]+", "_", text.strip().lower())
    return text.strip("_")


def name_for(title: str, content_tags: list[str]) -> str:
    number = re.search(r"(\d+)", title).group(1)
    if content_tags:
        return f"{slugify(content_tags[0])}_{number}"
    return f"nevit_{number}"


def main(meta_path: str, categorized_path: str, svg_dir: str) -> None:
    meta = json.loads(Path(meta_path).read_text())
    categorized = json.loads(Path(categorized_path).read_text())
    svg_dir = Path(svg_dir)

    index_path = EXAMPLES_DIR / "index.json"
    index = json.loads(index_path.read_text())
    existing_files = {entry["file"] for entry in index["figures"]}

    ok, failed, skipped = 0, [], 0
    for title, info in categorized.items():
        fname = title.replace("File:", "").replace(" ", "_")
        # Skip non-figure files (no number in title, or not an SVG)
        if not re.search(r"\d+", title) or not fname.lower().endswith(".svg"):
            skipped += 1
            continue
        svg_path = svg_dir / fname
        if not svg_path.exists() or svg_path.stat().st_size == 0:
            skipped += 1
            continue

        name = name_for(title, info["content_tags"])
        out_file = f"{name}.json"
        if out_file in existing_files:
            skipped += 1
            continue

        try:
            polygons = extract_polygons(svg_path.read_text())
            tangram = build_tangram(name, polygons)
            issues = validate(tangram)
            if issues:
                failed.append((title, f"validate: {issues}"))
                continue
        except Exception as e:
            failed.append((title, str(e)))
            continue

        description = ", ".join(info["content_tags"]) or "Tangram figure (Nevit Dilmen series)"
        tangram.description = description
        save_tangram(tangram, EXAMPLES_DIR / out_file)
        index["figures"].append(
            {"file": out_file, "category": info["bucket"], "source": "Nevit Dilmen (Wikimedia Commons, CC-BY-SA 3.0)", "tags": info["content_tags"]}
        )
        existing_files.add(out_file)
        ok += 1

    index_path.write_text(json.dumps(index, indent=2) + "\n")
    print(f"imported: {ok}, skipped (already present / not downloaded): {skipped}, failed: {len(failed)}")
    if failed:
        Path("/tmp/nevit_failed_import.json").write_text(json.dumps(failed, indent=2))
        print("failures written to /tmp/nevit_failed_import.json")
        for title, err in failed[:10]:
            print(" ", title, "->", err)


if __name__ == "__main__":
    main(sys.argv[1], sys.argv[2], sys.argv[3])
