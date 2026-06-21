"""Ask Claude to identify tangram figures from their silhouettes.

Renders each figure as a plain black-on-white silhouette (no piece colours,
no outlines, no labels) then sends the image to the Anthropic API and asks
what the shape looks like.  Useful for auditing existing titles and naming
newly imported figures that have generic placeholder titles.

Usage:
    python3 scripts/identify_tangrams.py                  # all figures in index.json
    python3 scripts/identify_tangrams.py cat.json bird.json
    python3 scripts/identify_tangrams.py --category people
"""
from __future__ import annotations

import argparse
import base64
import json
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent / "src"))

import os

import anthropic
import cairosvg

# Load ANTHROPIC_API_KEY from ~/.env if not already set in the environment.
if not os.environ.get("ANTHROPIC_API_KEY"):
    env_path = Path.home() / ".env"
    if env_path.exists():
        for line in env_path.read_text().splitlines():
            line = line.strip()
            if line.startswith("ANTHROPIC_API_KEY=") and not line.startswith("#"):
                os.environ["ANTHROPIC_API_KEY"] = line.split("=", 1)[1].strip()
                break

from tangram.io import load_tangram
from tangram.model import Tangram
from tangram.pieces import PieceType

# ---------------------------------------------------------------------------
# Silhouette renderer — produces a plain black-on-white SVG (no per-piece
# colours, no stroke) so the model sees only the shape.
# ---------------------------------------------------------------------------

VIEWBOX = 36  # generous margin around the 24-unit square


def _pts(verts) -> str:
    return " ".join(f"{v.x.to_float():.4f},{v.y.to_float():.4f}" for v in verts)


def silhouette_svg(tangram: Tangram, px: int = 300) -> str:
    all_verts = [v for p in tangram.pieces for v in p.vertices()]
    xs = [v.x.to_float() for v in all_verts]
    ys = [v.y.to_float() for v in all_verts]
    if not xs:
        return ""
    pad = 2.0
    vx, vy = min(xs) - pad, min(ys) - pad
    vw = (max(xs) - min(xs)) + pad * 2
    vh = (max(ys) - min(ys)) + pad * 2

    polygons = "\n".join(
        f'<polygon points="{_pts(p.vertices())}" />'
        for p in tangram.pieces
    )
    return (
        f'<svg xmlns="http://www.w3.org/2000/svg"'
        f' viewBox="{vx:.4f} {vy:.4f} {vw:.4f} {vh:.4f}"'
        f' width="{px}" height="{px}">'
        f'<rect x="{vx:.4f}" y="{vy:.4f}" width="{vw:.4f}" height="{vh:.4f}" fill="white"/>'
        f'<g fill="black" stroke="none">{polygons}</g>'
        f"</svg>"
    )


def svg_to_png_b64(svg_text: str, px: int = 300) -> str:
    png = cairosvg.svg2png(bytestring=svg_text.encode(), output_width=px, output_height=px)
    return base64.standard_b64encode(png).decode()


# ---------------------------------------------------------------------------
# Claude identification
# ---------------------------------------------------------------------------

PROMPT = (
    "This is a tangram silhouette — a solid black shape on white. "
    "Tangrams are puzzles made of 7 geometric pieces arranged to form a recognisable figure. "
    "What does this silhouette look like? "
    "Reply with a very short label (1–3 words, no punctuation). "
    "If it resembles a person or animal, say which one. "
    "If it looks geometric or abstract, describe the shape. "
    "Do not explain your reasoning."
)


def identify(tangram: Tangram, client: anthropic.Anthropic, model: str) -> str:
    svg = silhouette_svg(tangram)
    if not svg:
        return "(empty)"
    b64 = svg_to_png_b64(svg)
    msg = client.messages.create(
        model=model,
        max_tokens=32,
        messages=[
            {
                "role": "user",
                "content": [
                    {"type": "image", "source": {"type": "base64", "media_type": "image/png", "data": b64}},
                    {"type": "text", "text": PROMPT},
                ],
            }
        ],
    )
    return msg.content[0].text.strip()


# ---------------------------------------------------------------------------
# CLI
# ---------------------------------------------------------------------------


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    parser.add_argument("files", nargs="*", help="JSON filenames (basename only) to identify. Default: all in index.json")
    parser.add_argument("--category", help="Only identify figures in this category")
    parser.add_argument("--model", default="claude-haiku-4-5-20251001", help="Model to use")
    parser.add_argument("--examples-dir", default="examples", help="Path to examples directory")
    args = parser.parse_args()

    examples = Path(args.examples_dir)
    index = json.loads((examples / "index.json").read_text())

    if args.files:
        targets = [e for e in index["figures"] if e["file"] in args.files or e["file"].replace(".json", "") in args.files]
    elif args.category:
        targets = [e for e in index["figures"] if e["category"] == args.category]
    else:
        targets = index["figures"]

    client = anthropic.Anthropic()

    print(f"{'File':<28} {'Current title':<22} {'Claude says'}")
    print("-" * 72)
    for entry in targets:
        tangram = load_tangram(examples / entry["file"])
        guess = identify(tangram, client, args.model)
        current = entry.get("title", "(none)")
        marker = "" if current.lower() == guess.lower() else "  ←"
        print(f"{entry['file']:<28} {current:<22} {guess}{marker}")


if __name__ == "__main__":
    main()
