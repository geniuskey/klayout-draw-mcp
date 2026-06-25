"""Simple row-based placement (standard-cell style) and power rails.

``place_rows`` packs cells left-to-right into rows of a fixed width, wrapping to the
next row and (optionally) mirroring alternate rows the way abutted standard-cell rows
share power rails. It returns placements an assistant can feed to ``place_cell``.
"""

from __future__ import annotations


def place_rows(cells, row_width, row_pitch, x0=0.0, y0=0.0, flip_alt=False):
    """Greedily place cells into rows.

    cells: list of (name, width) in micrometers.
    row_width: maximum x extent of a row; row_pitch: vertical spacing between rows.
    Returns a list of dicts: {"name", "x", "y", "orient", "row"}.
    """
    placements = []
    x, row = x0, 0
    for name, w in cells:
        if x + w > x0 + row_width and x > x0:
            row += 1
            x = x0
        orient = "m0" if (flip_alt and row % 2 == 1) else "r0"
        placements.append({"name": name, "x": x, "y": y0 + row * row_pitch, "orient": orient, "row": row})
        x += w
    return placements


def power_rails(cell, ly, draw_box, n_rows, row_pitch, width, height,
                y0=0.0, rail_w=0.3, vdd="PWR", vss="PWR"):
    """Draw horizontal VDD/VSS rails at the top and bottom edge of each cell row."""
    for r in range(n_rows):
        y = y0 + r * row_pitch
        draw_box(cell, ly, vss, 0.0, y - rail_w / 2, width, y + rail_w / 2)            # bottom rail
        draw_box(cell, ly, vdd, 0.0, y + height - rail_w / 2, width, y + height + rail_w / 2)  # top rail
