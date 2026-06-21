"""Download Nevit Dilmen's tangram SVGs from Wikimedia Commons.

Fetches all 246 files from Category:Nevit_Dilmen_Tangrams, saves per-file
metadata (SVG download URL + Commons categories), and downloads the SVGs with
polite rate limiting.  Produces the two JSON files that bulk_import_nevit.py
expects.

Usage:
    python3 scripts/fetch_nevit.py /tmp/nevit_svgs
    # then:
    python3 scripts/bulk_import_nevit.py \
        /tmp/nevit_meta.json /tmp/nevit_categorized.json /tmp/nevit_svgs

The script is resumable: already-downloaded SVGs and already-fetched metadata
are skipped.  Run it again after an interruption and it picks up where it left
off.

Wikimedia API policy requires a descriptive User-Agent; ours identifies this
project and a contact address.
"""
from __future__ import annotations

import json
import re
import sys
import time
import urllib.parse
import urllib.request
from pathlib import Path

# ---------------------------------------------------------------------------
# Config
# ---------------------------------------------------------------------------

API = "https://commons.wikimedia.org/w/api.php"
DEFAULT_CATEGORY = "Category:Nevit_Dilmen_Tangrams"
USER_AGENT = "tangram-creation/1.0 (https://github.com/sebastiandelaile/tangram-creation; claude@mail.delaile.com) fetch_nevit.py"

API_DELAY = 1.0    # seconds between MediaWiki API calls
SVG_DELAY = 2.0    # seconds between SVG file downloads


# ---------------------------------------------------------------------------
# MediaWiki API helpers
# ---------------------------------------------------------------------------

def _api_get(params: dict) -> dict:
    url = API + "?" + urllib.parse.urlencode({**params, "format": "json", "formatversion": "2"})
    req = urllib.request.Request(url, headers={"User-Agent": USER_AGENT})
    with urllib.request.urlopen(req, timeout=30) as r:
        return json.loads(r.read())


def list_category_files(category: str = DEFAULT_CATEGORY) -> list[str]:
    """Return all file titles in category (e.g. 'File:Tangram 031 Nevit.svg')."""
    titles: list[str] = []
    params: dict = {
        "action": "query",
        "list": "categorymembers",
        "cmtitle": category,
        "cmlimit": "500",
        "cmtype": "file",
    }
    while True:
        data = _api_get(params)
        titles.extend(m["title"] for m in data["query"]["categorymembers"])
        if "continue" not in data:
            break
        params.update(data["continue"])
        time.sleep(API_DELAY)
    return titles


def fetch_file_info(titles: list[str]) -> dict[str, dict]:
    """
    For a batch of up to 50 file titles, return:
      { title: {"url": str, "categories": [str, ...]} }
    """
    params = {
        "action": "query",
        "titles": "|".join(titles),
        "prop": "imageinfo|categories",
        "iiprop": "url",
        "cllimit": "50",
    }
    data = _api_get(params)
    result: dict[str, dict] = {}
    for page in data["query"]["pages"]:
        title = page["title"]
        url = ""
        if page.get("imageinfo"):
            url = page["imageinfo"][0].get("url", "")
        cats = [c["title"].replace("Category:", "") for c in page.get("categories", [])]
        result[title] = {"url": url, "categories": cats}
    return result


# ---------------------------------------------------------------------------
# Categorisation
# ---------------------------------------------------------------------------

# Keywords that map each Commons category string to one of our buckets.
# Checked against joined category text (lowercased).
_BUCKET_RULES: list[tuple[str, list[str]]] = [
    ("letters",   ["letter", "number", "digit", "numeral", "alphabet"]),
    ("geometric", ["convex", "geometric shape"]),
    ("people",    ["people", "person", "human", "man", "woman", "runner",
                   "dancer", "figure", "yoga", "sitting person",
                   "kneeling", "standing"]),
    ("animals",   ["animal", "bird", "cat", "dog", "fish", "horse", "rabbit",
                   "duck", "swan", "fox", "deer", "elephant", "lion", "wolf",
                   "bear", "turtle", "frog", "camel", "monkey", "rooster",
                   "hen", "penguin", "goose", "crane", "cow", "pig", "sheep",
                   "mouse", "rat", "bat", "butterfly", "spider", "crab",
                   "lobster", "snail", "insect", "reptile", "mammal"]),
    ("objects",   ["object", "house", "boat", "vehicle", "tool", "bridge",
                   "candle", "chair", "table", "lamp", "arrow", "mountain",
                   "ship", "plane", "building", "furniture", "weapon",
                   "castle", "church", "tree", "plant", "flower"]),
]


def _bucket(cats: list[str]) -> str:
    joined = " ".join(cats).lower()
    for bucket, keywords in _BUCKET_RULES:
        if any(kw in joined for kw in keywords):
            return bucket
    return "abstract"


_TAG_PATTERNS = [
    # "Tangrams of horses by Nevit Dilmen" → "Horses"
    re.compile(r"[Tt]angrams?\s+of\s+(.+?)(?:\s+by\s+|\s*$)"),
    # "Horse tangrams by Nevit Dilmen" → "Horse"
    re.compile(r"^(.+?)\s+tangrams?", re.I),
    # "Horse riding in art" → "Horse riding"  (most specific subject category)
    re.compile(r"^(.+?)\s+in\s+art$", re.I),
]
_SKIP_WORDS = {"nevit", "dilmen", "tangram", "convex", "people", "animals",
               "objects", "letters", "numbers", "geometric", "shapes",
               "plain red svg animal icons", "unspec"}


def _content_tags(cats: list[str]) -> list[str]:
    tags: list[str] = []
    for cat in cats:
        # Skip Commons housekeeping categories
        low = cat.lower()
        if any(skip in low for skip in ("cc-by", "inkscape", "unspec", "svg created", "wikimedia")):
            continue
        for pat in _TAG_PATTERNS:
            m = pat.search(cat)
            if m:
                word = m.group(1).strip()
                lead = word.lower().split()[0]
                if lead not in _SKIP_WORDS and len(word) > 1:
                    tags.append(word.title())
                    break
    # Prefer shorter/more specific tags first (shorter = less generic)
    tags = sorted(set(tags), key=len)
    return tags


# ---------------------------------------------------------------------------
# Main
# ---------------------------------------------------------------------------

def main(svg_dir: str, category: str = DEFAULT_CATEGORY) -> None:
    out_dir = Path(svg_dir)
    out_dir.mkdir(parents=True, exist_ok=True)

    slug = re.sub(r"[^a-z0-9]+", "_", category.lower().replace("category:", "")).strip("_")
    meta_path = Path(f"/tmp/{slug}_meta.json")
    cat_path = Path(f"/tmp/{slug}_categorized.json")

    # --- Step 1: enumerate all files ----------------------------------------
    print(f"Listing files in {category} …", flush=True)
    all_titles = list_category_files(category)
    print(f"  found {len(all_titles)} files", flush=True)
    time.sleep(API_DELAY)

    # --- Step 2: fetch per-file URLs + categories (batches of 50) -----------
    meta: dict[str, dict] = {}
    if meta_path.exists():
        meta = json.loads(meta_path.read_text())
        print(f"Loaded {len(meta)} existing metadata entries from {meta_path}", flush=True)

    to_fetch = [t for t in all_titles if t not in meta]
    batch_size = 50
    total_batches = (len(to_fetch) + batch_size - 1) // batch_size
    print(f"Fetching metadata for {len(to_fetch)} files ({total_batches} batches) …", flush=True)

    for i in range(0, len(to_fetch), batch_size):
        batch = to_fetch[i : i + batch_size]
        batch_num = i // batch_size + 1
        print(f"  batch {batch_num}/{total_batches} …", end=" ", flush=True)
        info = fetch_file_info(batch)
        meta.update(info)
        meta_path.write_text(json.dumps(meta, indent=2))
        print(f"done ({len(info)} entries)", flush=True)
        time.sleep(API_DELAY)

    # --- Step 3: build categorized file -------------------------------------
    categorized: dict[str, dict] = {}
    for title, info in meta.items():
        cats = info["categories"]
        # Old metadata stored categories as a pipe-separated string; normalize.
        if isinstance(cats, str):
            cats = [c.strip() for c in cats.split("|") if c.strip()]
        categorized[title] = {
            "bucket": _bucket(cats),
            "content_tags": _content_tags(cats),
        }
    cat_path.write_text(json.dumps(categorized, indent=2))

    bucket_counts: dict[str, int] = {}
    for v in categorized.values():
        bucket_counts[v["bucket"]] = bucket_counts.get(v["bucket"], 0) + 1
    print("Category distribution:", bucket_counts, flush=True)
    print(f"Categorized file written to {cat_path}", flush=True)

    # --- Step 4: download SVGs ----------------------------------------------
    to_download = [
        (title, info["url"])
        for title, info in meta.items()
        if info["url"]
    ]
    already = sum(
        1 for _, url in to_download
        if (out_dir / Path(url).name).exists()
        and (out_dir / Path(url).name).stat().st_size > 0
    )
    print(f"Downloading SVGs: {len(to_download)} total, {already} already present …", flush=True)

    downloaded = skipped = failed = 0
    for title, url in to_download:
        fname = Path(url).name
        dest = out_dir / fname
        if dest.exists() and dest.stat().st_size > 0:
            skipped += 1
            continue
        try:
            req = urllib.request.Request(url, headers={"User-Agent": USER_AGENT})
            with urllib.request.urlopen(req, timeout=30) as r:
                dest.write_bytes(r.read())
            downloaded += 1
            print(f"  [{downloaded + skipped}/{len(to_download) - already + already}] {fname}", flush=True)
            time.sleep(SVG_DELAY)
        except Exception as e:
            failed += 1
            print(f"  FAILED {fname}: {e}", flush=True)

    print(f"\nDone. downloaded={downloaded}, skipped={skipped}, failed={failed}")
    print(f"\nNext step:")
    print(f"  python3 scripts/bulk_import_nevit.py {meta_path} {cat_path} {out_dir}")


if __name__ == "__main__":
    if len(sys.argv) not in (2, 3):
        print(f"Usage: python3 {sys.argv[0]} <output-svg-dir> [Category:Name]")
        sys.exit(1)
    cat = sys.argv[2] if len(sys.argv) == 3 else DEFAULT_CATEGORY
    main(sys.argv[1], cat)
