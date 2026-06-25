"""Basic shapes sample for klayout-draw-mcp.

Shows the four primitives (box, path, polygon, label) on a few layers.

Run standalone:
    uv run python examples/basic_shapes.py [out.gds]

Or paste the body of ``build()`` into the ``run_script`` MCP tool (``db`` is
injected there; ``ly``/``top`` map to ``session.layout``/``session.top``).
"""

from __future__ import annotations

import klayout.db as db

# Shared layer map used across the examples: name -> (layer, datatype)
LAYERS = {
    "OD": (3, 0),     # active / diffusion
    "POLY": (6, 0),   # gate poly
    "M1": (9, 0),     # metal 1
    "TEXT": (63, 0),  # labels
}


def build() -> db.Layout:
    ly = db.Layout()
    ly.dbu = 0.001  # 1 nm grid
    top = ly.create_cell("BASIC")

    def lay(name: str) -> int:
        return ly.layer(*LAYERS[name])

    def box(name, x1, y1, x2, y2):
        top.shapes(lay(name)).insert(db.DBox(x1, y1, x2, y2))

    def path(name, pts, width):
        top.shapes(lay(name)).insert(db.DPath([db.DPoint(*p) for p in pts], width))

    def polygon(name, pts):
        top.shapes(lay(name)).insert(db.DPolygon([db.DPoint(*p) for p in pts]))

    def label(name, x, y, text):
        top.shapes(lay(name)).insert(db.DText(text, db.DTrans(db.DVector(x, y))))

    # a rectangle
    box("OD", 0.0, 0.0, 5.0, 5.0)

    # a 0.5 um wide L-shaped path
    path("M1", [(0.0, 6.0), (5.0, 6.0), (5.0, 10.0)], 0.5)

    # a triangle polygon
    polygon("POLY", [(7.0, 0.0), (12.0, 0.0), (9.5, 5.0)])

    # a couple of labels
    label("TEXT", 2.5, 2.5, "box")
    label("TEXT", 9.5, 1.5, "polygon")

    return ly


if __name__ == "__main__":
    import sys

    out = sys.argv[1] if len(sys.argv) > 1 else "basic_shapes.gds"
    layout = build()
    layout.write(out)
    print(f"wrote {out}  bbox={layout.top_cell().dbbox().to_s()} um")
