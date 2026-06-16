"""Interactive Tkinter piece editor.

Click a piece to select it (topmost piece under the cursor wins), drag to
translate, R to rotate 45 degrees, F to flip (parallelogram only), S to save
back to the file it was loaded from.

Dragging snaps to the integer grid: the mouse delta is rounded to the nearest
whole unit before being added to the piece's anchor, so every placement stays
an exact Z[sqrt(2)] value -- no float drift creeps in even after many drags.

Usage: python -m tangram.gui [path/to/config.json]
"""
from __future__ import annotations

import sys
import tkinter as tk

from .algebra import Z2
from .geometry import Point
from .io import load_tangram, save_tangram
from .model import Tangram
from .pieces import PIECE_COLORS, PieceType

SCALE = 16.0
PADDING = 40
SELECTED_OUTLINE = "#000000"
SELECTED_WIDTH = 2.5


def _point_in_polygon(x: float, y: float, poly: list[tuple[float, float]]) -> bool:
    inside = False
    n = len(poly)
    for i in range(n):
        x1, y1 = poly[i]
        x2, y2 = poly[(i + 1) % n]
        if (y1 > y) != (y2 > y):
            x_at_y = x1 + (y - y1) * (x2 - x1) / (y2 - y1)
            if x < x_at_y:
                inside = not inside
    return inside


class Editor:
    def __init__(self, tangram: Tangram, path: str):
        self.tangram = tangram
        self.path = path
        self.selected_index: int | None = None
        self.drag_start_screen: tuple[float, float] | None = None
        self.drag_start_anchor: Point | None = None

        min_x, min_y, max_x, max_y = tangram.bounding_box()
        self.min_x, self.min_y = min_x, min_y
        width = (max_x - min_x) * SCALE + 2 * PADDING
        height = (max_y - min_y) * SCALE + 2 * PADDING

        self.root = tk.Tk()
        self.root.title(f"Tangram editor - {tangram.name}")
        self.canvas = tk.Canvas(self.root, width=width, height=height, bg="white")
        self.canvas.pack()
        self.status = tk.Label(self.root, text="", anchor="w", font=("Menlo", 11))
        self.status.pack(fill="x")

        self.canvas.bind("<ButtonPress-1>", self.on_press)
        self.canvas.bind("<B1-Motion>", self.on_drag)
        self.canvas.bind("<ButtonRelease-1>", self.on_release)
        self.root.bind("<Key-r>", self.on_rotate)
        self.root.bind("<Key-f>", self.on_flip)
        self.root.bind("<Key-s>", self.on_save)

        self.redraw()

    def to_screen(self, p: Point) -> tuple[float, float]:
        x, y = p.to_float()
        return ((x - self.min_x) * SCALE + PADDING, (y - self.min_y) * SCALE + PADDING)

    def piece_screen_polygon(self, index: int) -> list[tuple[float, float]]:
        return [self.to_screen(v) for v in self.tangram.pieces[index].vertices()]

    def redraw(self) -> None:
        self.canvas.delete("all")
        for i, piece in enumerate(self.tangram.pieces):
            poly = self.piece_screen_polygon(i)
            color = PIECE_COLORS[piece.piece_type]
            is_selected = i == self.selected_index
            self.canvas.create_polygon(
                *[c for point in poly for c in point],
                fill=color,
                outline=SELECTED_OUTLINE if is_selected else "#1a1a1a",
                width=SELECTED_WIDTH if is_selected else 1,
            )
        self.update_status()

    def update_status(self) -> None:
        if self.selected_index is None:
            self.status.config(text="Click a piece to select it. R=rotate F=flip S=save")
            return
        p = self.tangram.pieces[self.selected_index]
        self.status.config(
            text=(
                f"Selected: {p.piece_type.value} #{p.piece_id}  "
                f"anchor=({p.anchor.x}, {p.anchor.y})  "
                f"orientation={p.orientation * 45}deg  flipped={p.flipped}   "
                f"[R]otate [F]lip [S]ave"
            )
        )

    def find_piece_at(self, x: float, y: float) -> int | None:
        for i in reversed(range(len(self.tangram.pieces))):
            if _point_in_polygon(x, y, self.piece_screen_polygon(i)):
                return i
        return None

    def on_press(self, event: tk.Event) -> None:
        index = self.find_piece_at(event.x, event.y)
        self.selected_index = index
        if index is not None:
            self.drag_start_screen = (event.x, event.y)
            self.drag_start_anchor = self.tangram.pieces[index].anchor
        self.redraw()

    def on_drag(self, event: tk.Event) -> None:
        if self.selected_index is None or self.drag_start_screen is None:
            return
        dx_screen = event.x - self.drag_start_screen[0]
        dy_screen = event.y - self.drag_start_screen[1]
        dx = round(dx_screen / SCALE)
        dy = round(dy_screen / SCALE)
        new_anchor = self.drag_start_anchor + Point(Z2.of(dx, 0), Z2.of(dy, 0))
        old = self.tangram.pieces[self.selected_index]
        self.tangram.pieces[self.selected_index] = type(old)(
            old.piece_type, old.piece_id, new_anchor, old.orientation, old.flipped
        )
        self.redraw()

    def on_release(self, event: tk.Event) -> None:
        self.drag_start_screen = None
        self.drag_start_anchor = None

    def on_rotate(self, event: tk.Event) -> None:
        if self.selected_index is None:
            return
        self.tangram.pieces[self.selected_index] = self.tangram.pieces[
            self.selected_index
        ].rotated(1)
        self.redraw()

    def on_flip(self, event: tk.Event) -> None:
        if self.selected_index is None:
            return
        piece = self.tangram.pieces[self.selected_index]
        if piece.piece_type != PieceType.PARALLELOGRAM:
            return
        self.tangram.pieces[self.selected_index] = piece.flipped_copy()
        self.redraw()

    def on_save(self, event: tk.Event) -> None:
        save_tangram(self.tangram, self.path)
        self.status.config(text=f"Saved to {self.path}")

    def run(self) -> None:
        self.root.mainloop()


def main() -> None:
    path = sys.argv[1] if len(sys.argv) > 1 else "examples/cat.json"
    tangram = load_tangram(path)
    Editor(tangram, path).run()


if __name__ == "__main__":
    main()
