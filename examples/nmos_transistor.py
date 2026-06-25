"""Single NMOS transistor sample for klayout-draw-mcp.

A planar n-channel MOSFET (W = 1 um, L = 0.4 um): active diffusion, a poly
gate crossing the channel, n+ source/drain implant, contacts and metal-1 pads
for source (S), gate (G) and drain (D).

Run standalone:
    uv run python examples/nmos_transistor.py [out.gds]

Or paste the body of ``build()`` into the ``run_script`` MCP tool.
"""

from __future__ import annotations

import klayout.db as db

# Shared layer map: name -> (layer, datatype)
LAYERS = {
    "PWELL": (2, 0),
    "OD": (3, 0),     # active / diffusion
    "NPLUS": (4, 0),  # n+ source/drain implant
    "POLY": (6, 0),   # gate poly
    "CONT": (8, 0),   # contact
    "M1": (9, 0),     # metal 1
    "TEXT": (63, 0),  # labels
}


def build() -> db.Layout:
    ly = db.Layout()
    ly.dbu = 0.001
    top = ly.create_cell("NMOS")

    def lay(name: str) -> int:
        return ly.layer(*LAYERS[name])

    def box(name, x1, y1, x2, y2):
        top.shapes(lay(name)).insert(db.DBox(x1, y1, x2, y2))

    def label(name, x, y, text):
        top.shapes(lay(name)).insert(db.DText(text, db.DTrans(db.DVector(x, y))))

    # well + active + implant
    box("PWELL", -0.3, -0.5, 2.3, 1.9)
    box("NPLUS", -0.1, -0.1, 2.1, 1.1)
    box("OD", 0.0, 0.0, 2.0, 1.0)          # W = 1.0 um

    # poly gate crossing the channel (L = 0.4 um), extended up for a contact
    box("POLY", 0.8, -0.3, 1.2, 1.6)

    # contacts: two on source, two on drain, one on the gate landing
    for cy in (0.3, 0.7):
        box("CONT", 0.25, cy - 0.1, 0.45, cy + 0.1)   # source
        box("CONT", 1.55, cy - 0.1, 1.75, cy + 0.1)   # drain
    box("CONT", 0.9, 1.2, 1.1, 1.4)                    # gate

    # metal-1 pads
    box("M1", 0.15, 0.15, 0.55, 0.85)   # S
    box("M1", 1.45, 0.15, 1.85, 0.85)   # D
    box("M1", 0.75, 1.1, 1.25, 1.5)     # G

    label("TEXT", 0.35, 0.5, "S")
    label("TEXT", 1.0, 1.7, "G")
    label("TEXT", 1.65, 0.5, "D")

    return ly


if __name__ == "__main__":
    import sys

    out = sys.argv[1] if len(sys.argv) > 1 else "nmos.gds"
    layout = build()
    layout.write(out)
    print(f"wrote {out}  bbox={layout.top_cell().dbbox().to_s()} um")
