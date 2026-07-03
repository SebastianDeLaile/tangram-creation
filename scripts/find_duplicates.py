"""Find duplicate tangram *solutions* in the library by silhouette matching.

Two figures are the same solution if their outlines are congruent -- the same
shape up to translation, rotation (any multiple of 90 deg here) and reflection --
even if named differently or built from a slightly different piece breakdown.

Each figure's silhouette is rendered to a small normalized bitmap; every pair is
compared under the 8 dihedral symmetries and scored by intersection-over-union.
Pairs above THRESHOLD are reported as likely duplicates.

Usage:
    python3 scripts/find_duplicates.py            # scan whole library
"""
from __future__ import annotations
import sys, json, io
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent / "src"))
sys.path.insert(0, str(Path(__file__).resolve().parent))

import cairosvg
from PIL import Image, ImageChops
from tangram.io import load_tangram

# All tangram figures have the SAME area, so we render every silhouette at a
# FIXED units->pixels scale (not fit-to-box) and align by centroid.  Identical
# silhouettes then overlap almost perfectly (IoU ~1) while different shapes score
# far lower -- fit-to-box scaling instead made every blob look ~93% alike.
SCALE = 6.0       # pixels per unit
CANVAS = 440      # square canvas (big enough to rotate without clipping)
THRESHOLD = 0.98  # min IoU (best over 8 symmetries) to call a pair duplicate


def silhouette_bitmap(tg) -> Image.Image:
    verts = [v for p in tg.pieces for v in p.vertices()]
    xs = [v.x.to_float() for v in verts]
    ys = [v.y.to_float() for v in verts]
    minx, miny = min(xs), min(ys)
    w = (max(xs) - minx) or 1.0
    h = (max(ys) - miny) or 1.0
    polys = "".join(
        '<polygon points="' + " ".join(f"{v.x.to_float()-minx:.3f},{v.y.to_float()-miny:.3f}"
                                        for v in p.vertices()) + '" fill="black"/>'
        for p in tg.pieces
    )
    svg = (f'<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 {w:.3f} {h:.3f}">'
           f'<rect x="0" y="0" width="{w:.3f}" height="{h:.3f}" fill="white"/>{polys}</svg>')
    pw, ph = max(1, round(w * SCALE)), max(1, round(h * SCALE))
    png = cairosvg.svg2png(bytestring=svg.encode(), output_width=pw, output_height=ph)
    fig = Image.open(io.BytesIO(png)).convert("L").point(lambda p: 255 if p < 128 else 0)
    px = fig.load()
    sx = sy = cnt = 0
    for yy in range(ph):
        for xx in range(pw):
            if px[xx, yy]:
                sx += xx; sy += yy; cnt += 1
    cx, cy = (sx / cnt, sy / cnt) if cnt else (pw / 2, ph / 2)
    canvas = Image.new("L", (CANVAS, CANVAS), 0)
    canvas.paste(fig, (round(CANVAS // 2 - cx), round(CANVAS // 2 - cy)))
    return canvas.convert("1")


def symmetries(img: Image.Image) -> list[Image.Image]:
    out = []
    for base in (img, img.transpose(Image.FLIP_LEFT_RIGHT)):
        for k in range(4):
            out.append(base.rotate(90 * k))
    return out


def iou(a: Image.Image, b: Image.Image) -> float:
    inter = ImageChops.logical_and(a, b).histogram()[-1]
    union = ImageChops.logical_or(a, b).histogram()[-1]
    return inter / union if union else 0.0


def main() -> None:
    idx = json.loads(Path("examples/index.json").read_text())
    figs = idx["figures"]
    print(f"scanning {len(figs)} figures (scale={SCALE}, threshold={THRESHOLD})...")
    bmp = {}
    syms = {}
    for e in figs:
        tg = load_tangram(Path("examples") / e["file"])
        bmp[e["file"]] = silhouette_bitmap(tg)
        syms[e["file"]] = symmetries(bmp[e["file"]])

    pairs = []
    files = [e["file"] for e in figs]
    title = {e["file"]: e.get("title", "") for e in figs}
    for i in range(len(files)):
        a = bmp[files[i]]
        for j in range(i + 1, len(files)):
            best = max(iou(a, s) for s in syms[files[j]])
            if best >= THRESHOLD:
                pairs.append((best, files[i], files[j]))
    pairs.sort(reverse=True)
    print(f"\n{len(pairs)} likely-duplicate pair(s):")
    for score, a, b in pairs:
        print(f"  {score:.3f}  {title[a]:14} ({a})  ==  {title[b]:14} ({b})")


if __name__ == "__main__":
    main()
