"""CMOS inverter sample for klayout-draw-mcp.

A pull-up PMOS (in an n-well, top) over a pull-down NMOS (in the p-well,
bottom) sharing one poly gate (the input). The two drains are tied together
on metal-1 (the output). Power rails: Vdd on top, Vss on the bottom, plus
well ties.

Run standalone:
    uv run python examples/cmos_inverter.py [out.gds]

Or paste the body of ``build()`` into the ``run_script`` MCP tool.
"""

from __future__ import annotations

import klayout.db as db

# Shared layer map: name -> (layer, datatype)
LAYERS = {
    "NWELL": (1, 0),
    "PWELL": (2, 0),
    "OD": (3, 0),     # active / diffusion
    "NPLUS": (4, 0),  # n+ implant (nmos s/d, n-well tie)
    "PPLUS": (5, 0),  # p+ implant (pmos s/d, p-well tie)
    "POLY": (6, 0),   # gate poly
    "CONT": (8, 0),
    "M1": (9, 0),
    "TEXT": (63, 0),
}


def build() -> db.Layout:
    ly = db.Layout()
    ly.dbu = 0.001
    top = ly.create_cell("INVERTER")

    def lay(name: str) -> int:
        return ly.layer(*LAYERS[name])

    def box(name, x1, y1, x2, y2):
        top.shapes(lay(name)).insert(db.DBox(x1, y1, x2, y2))

    def label(name, x, y, text):
        top.shapes(lay(name)).insert(db.DText(text, db.DTrans(db.DVector(x, y))))

    # wells (p-well bottom, n-well top)
    box("PWELL", 0.0, 0.0, 3.0, 2.0)
    box("NWELL", 0.0, 2.0, 3.0, 4.0)

    # transistor active areas
    box("OD", 0.6, 0.6, 2.4, 1.4)    # NMOS
    box("OD", 0.6, 2.6, 2.4, 3.4)    # PMOS
    box("NPLUS", 0.5, 0.5, 2.5, 1.5)
    box("PPLUS", 0.5, 2.5, 2.5, 3.5)

    # well ties along the rails (p+ tie in p-well, n+ tie in n-well)
    box("OD", 0.6, 0.05, 2.4, 0.25)
    box("PPLUS", 0.5, 0.0, 2.5, 0.3)
    box("OD", 0.6, 3.75, 2.4, 3.95)
    box("NPLUS", 0.5, 3.7, 2.5, 4.0)

    # shared poly gate (input), vertical, crossing both actives
    box("POLY", 1.3, 0.2, 1.7, 3.8)

    # contacts
    def cont(cx, cy):
        box("CONT", cx - 0.1, cy - 0.1, cx + 0.1, cy + 0.1)

    cont(0.9, 1.0)    # NMOS source -> Vss
    cont(2.1, 1.0)    # NMOS drain  -> Out
    cont(0.9, 3.0)    # PMOS source -> Vdd
    cont(2.1, 3.0)    # PMOS drain  -> Out
    cont(1.5, 2.0)    # gate (input)
    cont(1.5, 0.15)   # p-well tie
    cont(1.5, 3.85)   # n-well tie

    # metal-1
    box("M1", 0.0, 0.0, 3.0, 0.3)     # Vss rail
    box("M1", 0.0, 3.7, 3.0, 4.0)     # Vdd rail
    box("M1", 0.75, 0.0, 1.05, 1.2)   # NMOS source -> Vss
    box("M1", 0.75, 2.8, 1.05, 4.0)   # PMOS source -> Vdd
    box("M1", 1.95, 0.9, 2.25, 3.1)   # Out: ties both drains
    box("M1", 0.0, 1.85, 1.65, 2.15)  # In: gate -> left edge

    label("TEXT", 1.4, 3.85, "Vdd")
    label("TEXT", 1.4, 0.1, "Vss")
    label("TEXT", 0.15, 2.0, "In")
    label("TEXT", 2.3, 2.0, "Out")

    return ly


if __name__ == "__main__":
    import sys

    out = sys.argv[1] if len(sys.argv) > 1 else "inverter.gds"
    layout = build()
    layout.write(out)
    print(f"wrote {out}  bbox={layout.top_cell().dbbox().to_s()} um")
