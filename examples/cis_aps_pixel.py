"""CIS 4T active-pixel-sensor (APS) sample for klayout-draw-mcp.

A simplified 1 um 4T CMOS image-sensor pixel: a large photodiode (PD), a
transfer gate (TX) to the floating diffusion (FD), and reset (RST),
source-follower (SF) and row-select (SEL) transistors in the shared active
column. The unit pixel is drawn into its own cell and instanced as a 2x2
array, the way a real sensor array repeats.

Run standalone:
    uv run python examples/cis_aps_pixel.py [out.gds]

Or paste the body of ``build()`` into the ``run_script`` MCP tool.
"""

from __future__ import annotations

import klayout.db as db

# Shared layer map: name -> (layer, datatype)
LAYERS = {
    "PWELL": (2, 0),
    "OD": (3, 0),     # active / diffusion
    "NPLUS": (4, 0),  # n+ implant
    "PPLUS": (5, 0),  # p+ well tap
    "POLY": (6, 0),   # gate poly (TX / RST / SF / SEL)
    "CONT": (8, 0),
    "M1": (9, 0),
    "PD": (10, 0),    # photodiode n-implant
    "TEXT": (63, 0),
    "BND": (100, 0),  # pixel boundary marker
}

PIXEL_PITCH = 1.0  # um
ARRAY = (2, 2)     # columns, rows


def build() -> db.Layout:
    ly = db.Layout()
    ly.dbu = 0.001
    top = ly.create_cell("CIS_APS")
    pix = ly.create_cell("APS_PIXEL")

    def lay(name: str) -> int:
        return ly.layer(*LAYERS[name])

    def box(name, x1, y1, x2, y2):
        pix.shapes(lay(name)).insert(db.DBox(x1, y1, x2, y2))

    def label(name, x, y, text):
        pix.shapes(lay(name)).insert(db.DText(text, db.DTrans(db.DVector(x, y))))

    def cont(cx, cy):
        box("CONT", cx - 0.02, cy - 0.02, cx + 0.02, cy + 0.02)

    # pixel boundary + well
    box("BND", 0.0, 0.0, 1.0, 1.0)
    box("PWELL", 0.0, 0.0, 1.0, 1.0)

    # photodiode (left, large fill factor)
    box("PD", 0.05, 0.05, 0.55, 0.95)
    box("OD", 0.08, 0.08, 0.52, 0.92)

    # transfer gate TX, bridging PD -> FD
    box("POLY", 0.50, 0.58, 0.60, 0.82)

    # floating diffusion FD
    box("OD", 0.58, 0.60, 0.70, 0.80)
    box("NPLUS", 0.57, 0.59, 0.71, 0.81)

    # shared transistor active column on the right
    box("OD", 0.70, 0.06, 0.94, 0.94)
    box("NPLUS", 0.69, 0.05, 0.95, 0.95)

    # RST / SF / SEL gates (horizontal poly across the column)
    box("POLY", 0.66, 0.66, 0.97, 0.74)   # RST
    box("POLY", 0.66, 0.40, 0.97, 0.48)   # SF
    box("POLY", 0.66, 0.16, 0.97, 0.24)   # SEL

    # p-well tap (Vss), bottom-left
    box("OD", 0.10, 0.10, 0.24, 0.20)
    box("PPLUS", 0.09, 0.09, 0.25, 0.21)

    # contacts
    cont(0.64, 0.70)                      # FD
    cont(0.18, 0.15)                      # Vss tap
    for cy in (0.11, 0.32, 0.57, 0.84):   # right column source/drains
        cont(0.82, cy)
    cont(0.69, 0.70)                      # RST gate
    cont(0.69, 0.44)                      # SF gate
    cont(0.69, 0.20)                      # SEL gate

    # metal-1: FD -> SF gate strap, and a Vdd rail
    box("M1", 0.62, 0.68, 0.72, 0.72)
    box("M1", 0.66, 0.44, 0.72, 0.72)
    box("M1", 0.88, 0.06, 0.95, 0.94)

    # labels
    label("TEXT", 0.26, 0.48, "PD")
    label("TEXT", 0.50, 0.86, "TX")
    label("TEXT", 0.60, 0.83, "FD")
    label("TEXT", 0.74, 0.69, "RST")
    label("TEXT", 0.76, 0.43, "SF")
    label("TEXT", 0.74, 0.19, "SEL")
    label("TEXT", 0.10, 0.23, "Vss")
    label("TEXT", 0.90, 0.965, "Vdd")

    # tile the unit pixel into a 2x2 array
    nx, ny = ARRAY
    top.insert(
        db.DCellInstArray(
            pix.cell_index(),
            db.DTrans(db.DVector(0.0, 0.0)),
            db.DVector(PIXEL_PITCH, 0.0),
            db.DVector(0.0, PIXEL_PITCH),
            nx,
            ny,
        )
    )
    return ly


if __name__ == "__main__":
    import sys

    out = sys.argv[1] if len(sys.argv) > 1 else "cis_aps.gds"
    layout = build()
    layout.write(out)
    print(f"wrote {out}  bbox={layout.top_cell().dbbox().to_s()} um")
