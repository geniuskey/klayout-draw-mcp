"""Shared helpers for the klayout-pnr recipes: layer map, geometry, routing grid.

Pure ``klayout.db`` so the recipes run standalone (``python demo_pnr.py``) and can
also be pasted into the MCP ``run_script`` tool (where ``db`` is already injected).
"""

from __future__ import annotations

import klayout.db as db

# Shared layer map (matches the examples/ gallery): name -> (layer, datatype)
LAYERS = {
    "OD": (3, 0),
    "NPLUS": (4, 0),
    "PPLUS": (5, 0),
    "POLY": (6, 0),
    "CONT": (8, 0),
    "M1": (9, 0),
    "VIA1": (11, 0),
    "M2": (12, 0),
    "TEXT": (63, 0),
    "PWR": (90, 0),     # power rails
    "BLOCK": (200, 0),  # routing blockage / debug marker
}


def layer(ly: db.Layout, name: str) -> int:
    return ly.layer(*LAYERS[name])


def draw_box(cell: db.Cell, ly: db.Layout, name: str, x1, y1, x2, y2) -> None:
    cell.shapes(layer(ly, name)).insert(db.DBox(x1, y1, x2, y2))


def draw_wire(cell: db.Cell, ly: db.Layout, name: str, pts, width: float) -> None:
    cell.shapes(layer(ly, name)).insert(db.DPath([db.DPoint(x, y) for x, y in pts], width))


def draw_via(cell, ly, x, y, bottom="M1", top="M2", cut="VIA1", size=0.1, enc=0.05) -> None:
    draw_box(cell, ly, cut, x - size / 2, y - size / 2, x + size / 2, y + size / 2)
    for m in (bottom, top):
        draw_box(cell, ly, m, x - size / 2 - enc, y - size / 2 - enc, x + size / 2 + enc, y + size / 2 + enc)


class RoutingGrid:
    """Maps micrometer coordinates to integer routing-grid nodes and back."""

    def __init__(self, x0: float, y0: float, nx: int, ny: int, pitch: float):
        self.x0, self.y0, self.nx, self.ny, self.pitch = x0, y0, nx, ny, pitch

    def col(self, x: float) -> int:
        return round((x - self.x0) / self.pitch)

    def row(self, y: float) -> int:
        return round((y - self.y0) / self.pitch)

    def x(self, c: int) -> float:
        return self.x0 + c * self.pitch

    def y(self, r: int) -> float:
        return self.y0 + r * self.pitch

    def node(self, x: float, y: float):
        return (self.col(x), self.row(y))

    def point(self, c: int, r: int):
        return (self.x(c), self.y(r))

    def block_box(self, blocked: set, x1, y1, x2, y2) -> None:
        """Mark grid nodes strictly inside (x1,y1)-(x2,y2) as blocked (half-open top/right)."""
        for c in range(max(0, self.col(x1)), min(self.nx, self.col(x2))):
            for r in range(max(0, self.row(y1)), min(self.ny, self.row(y2))):
                if self.x(c) >= x1 and self.y(r) >= y1:
                    blocked.add((c, r))
