"""End-to-end auto place-and-route demo on klayout.db.

Defines one standard cell, places six instances in two rows (with routing channels),
then connects a chain of nets with the obstacle-aware maze router and draws the wires
on M1. Demonstrates the technique stack the skill describes.

    uv run python skills/klayout-pnr/scripts/demo_pnr.py [out.gds]
"""

from __future__ import annotations

import os
import sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

import klayout.db as db  # noqa: E402

from maze_router import route_net  # noqa: E402
from pnr_helpers import RoutingGrid, draw_box, draw_wire  # noqa: E402

W, H = 2.0, 2.0          # cell width / height
XS = [0.0, 2.5, 5.0]     # column origins (0.5 um vertical routing channels between)
YS = [0.0, 4.0]          # row origins (2.0 um horizontal routing channel above each)
PITCH = 0.25             # routing-grid pitch


def build() -> db.Layout:
    ly = db.Layout()
    ly.dbu = 0.001
    top = ly.create_cell("PNR_TOP")

    # one reusable standard cell with two M1 pins (A, B) on the top edge
    std = ly.create_cell("STD")
    draw_box(std, ly, "OD", 0.1, 0.1, W - 0.1, H - 0.1)
    draw_box(std, ly, "POLY", W / 2 - 0.1, -0.1, W / 2 + 0.1, H + 0.1)
    draw_box(std, ly, "M1", 0.3, H - 0.3, 0.7, H)   # pin A (x=0.5)
    draw_box(std, ly, "M1", 1.3, H - 0.3, 1.7, H)   # pin B (x=1.5)

    cells = []
    for y in YS:
        for x in XS:
            top.insert(db.DCellInstArray(std.cell_index(), db.DTrans(db.DVector(x, y))))
            cells.append((x, y))

    pin_a = [(x + 0.5, y + H) for (x, y) in cells]
    pin_b = [(x + 1.5, y + H) for (x, y) in cells]

    nx = round(7.0 / PITCH) + 1
    ny = round(8.0 / PITCH) + 1
    grid = RoutingGrid(0.0, 0.0, nx, ny, PITCH)

    blocked: set = set()
    for (x, y) in cells:
        grid.block_box(blocked, x, y, x + W, y + H)

    # net chain: B_i -> A_{i+1}
    nets = [(pin_b[i], pin_a[i + 1]) for i in range(len(cells) - 1)]
    routed = 0
    for p1, p2 in nets:
        pts = route_net(grid, blocked, p1, p2)
        if pts is None:
            print(f"  UNROUTED {p1} -> {p2}")
            continue
        draw_wire(top, ly, "M1", pts, 0.15)
        routed += 1
    print(f"routed {routed}/{len(nets)} nets")
    return ly


if __name__ == "__main__":
    out = sys.argv[1] if len(sys.argv) > 1 else "pnr_demo.gds"
    layout = build()
    layout.write(out)
    print(f"wrote {out}  bbox={layout.top_cell().dbbox().to_s()} um")
