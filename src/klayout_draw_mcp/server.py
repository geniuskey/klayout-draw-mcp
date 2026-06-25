"""KLayout MCP server.

Two complementary ways to produce GDS layouts:

1. High-level drawing tools (`new_layout`, `add_box`, `add_polygon`, ...) build an
   in-memory layout step by step using the standalone ``klayout.db`` module.
2. `run_script` executes arbitrary Python with ``klayout.db`` available, for anything
   the high-level tools do not cover (cell hierarchy, arrays, boolean ops, DRC, ...).

Plus `open_layout` / `open_editor` to launch the installed KLayout application for
viewing or manual drawing.

All coordinates in the high-level tools are in micrometers.
"""

from __future__ import annotations

import io
import os
import shutil
import subprocess
import sys
from contextlib import redirect_stdout
from dataclasses import dataclass
from pathlib import Path
from typing import Optional

import klayout
import klayout.db as db
from mcp.server.fastmcp import FastMCP

mcp = FastMCP("klayout")


# ---------------------------------------------------------------------------
# KLayout application discovery (for viewer / editor)
# ---------------------------------------------------------------------------
def _find_klayout_exe() -> Optional[str]:
    exe = shutil.which("klayout")
    if exe:
        return exe
    if sys.platform == "win32":
        candidates = [
            os.path.join(os.environ.get("APPDATA", ""), "KLayout", "klayout_app.exe"),
            os.path.join(os.environ.get("ProgramFiles", ""), "KLayout", "klayout_app.exe"),
            os.path.join(os.environ.get("LOCALAPPDATA", ""), "Programs", "KLayout", "klayout_app.exe"),
        ]
        for c in candidates:
            if c and os.path.isfile(c):
                return c
    return None


def _launch_app(args: list[str]) -> str:
    """Launch the KLayout GUI detached. Returns the command string used."""
    exe = _find_klayout_exe()
    if exe:
        cmd = [exe, *args]
    elif sys.platform == "darwin":
        cmd = ["open", "-a", "KLayout", "--args", *args]
    else:
        raise RuntimeError(
            "KLayout application not found. Install KLayout and ensure it is on PATH "
            "or in a default location."
        )
    subprocess.Popen(cmd, close_fds=True)
    return " ".join(cmd)


# ---------------------------------------------------------------------------
# In-memory drawing session
# ---------------------------------------------------------------------------
@dataclass
class LayoutSession:
    layout: db.Layout
    top: db.Cell

    @classmethod
    def create(cls, top_cell: str, dbu: float) -> "LayoutSession":
        ly = db.Layout()
        ly.dbu = dbu
        return cls(layout=ly, top=ly.create_cell(top_cell))

    def layer(self, layer: int, datatype: int) -> int:
        return self.layout.layer(layer, datatype)


_session: Optional[LayoutSession] = None


def _require_session() -> LayoutSession:
    if _session is None:
        raise RuntimeError("No active layout. Call new_layout() first.")
    return _session


# ---------------------------------------------------------------------------
# High-level drawing tools (coordinates in micrometers)
# ---------------------------------------------------------------------------
@mcp.tool()
def new_layout(top_cell: str = "TOP", dbu: float = 0.001) -> str:
    """Start a new in-memory layout to draw into.

    top_cell: name of the top cell. dbu: database unit in micrometers
    (0.001 = 1 nm grid). Resets any previous in-memory layout.
    """
    global _session
    _session = LayoutSession.create(top_cell, dbu)
    return f"New layout started: top_cell='{top_cell}', dbu={dbu} um."


@mcp.tool()
def add_box(layer: int, x1: float, y1: float, x2: float, y2: float, datatype: int = 0) -> str:
    """Add a rectangle (micrometers) on GDS layer/datatype."""
    s = _require_session()
    s.top.shapes(s.layer(layer, datatype)).insert(db.DBox(x1, y1, x2, y2))
    return f"Box on {layer}/{datatype}: ({x1},{y1})-({x2},{y2}) um."


@mcp.tool()
def add_polygon(layer: int, points: list[list[float]], datatype: int = 0) -> str:
    """Add a polygon from a list of [x, y] vertices (micrometers)."""
    s = _require_session()
    pts = [db.DPoint(p[0], p[1]) for p in points]
    s.top.shapes(s.layer(layer, datatype)).insert(db.DPolygon(pts))
    return f"Polygon ({len(pts)} pts) on {layer}/{datatype}."


@mcp.tool()
def add_path(layer: int, points: list[list[float]], width: float, datatype: int = 0) -> str:
    """Add a path: centerline [x, y] points (micrometers) with the given width."""
    s = _require_session()
    pts = [db.DPoint(p[0], p[1]) for p in points]
    s.top.shapes(s.layer(layer, datatype)).insert(db.DPath(pts, width))
    return f"Path ({len(pts)} pts, width={width}) on {layer}/{datatype}."


@mcp.tool()
def add_label(layer: int, x: float, y: float, text: str, datatype: int = 0) -> str:
    """Add a text label at (x, y) micrometers."""
    s = _require_session()
    s.top.shapes(s.layer(layer, datatype)).insert(db.DText(text, db.DTrans(db.DVector(x, y))))
    return f"Label '{text}' at ({x},{y}) on {layer}/{datatype}."


@mcp.tool()
def layout_info() -> str:
    """Report the current layout: top cell, dbu, layers, bbox, shape count."""
    s = _require_session()
    idxs = list(s.layout.layer_indexes())
    layers = [f"{s.layout.get_info(i).layer}/{s.layout.get_info(i).datatype}" for i in idxs]
    shapes = sum(s.top.shapes(i).size() for i in idxs)
    return (
        f"top_cell='{s.top.name}', dbu={s.layout.dbu} um\n"
        f"layers: {', '.join(layers) or '(none)'}\n"
        f"bbox: {s.top.dbbox().to_s()} um\n"
        f"shapes: {shapes}"
    )


@mcp.tool()
def save_gds(path: str, open_after: bool = False) -> str:
    """Write the current layout to a file (.gds/.oas by extension). Optionally open it in the editor."""
    s = _require_session()
    out = Path(path).expanduser()
    out.parent.mkdir(parents=True, exist_ok=True)
    s.layout.write(str(out))
    msg = f"Saved {out} ({out.stat().st_size} bytes)."
    if open_after:
        try:
            msg += f" Opened in editor: {_launch_app(['-e', str(out)])}"
        except Exception as e:  # noqa: BLE001
            msg += f" (open failed: {e})"
    return msg


# ---------------------------------------------------------------------------
# Application launch (viewer / editor)
# ---------------------------------------------------------------------------
@mcp.tool()
def open_layout(file_path: str) -> str:
    """Open an existing layout file in KLayout (viewer mode)."""
    p = Path(file_path).expanduser()
    if not p.is_file():
        raise RuntimeError(f"File not found: {p}")
    return f"KLayout viewer launched: {_launch_app([str(p)])}"


@mcp.tool()
def open_editor(file_path: Optional[str] = None) -> str:
    """Open KLayout in editor mode (-e). With a file: edit it. Without: a blank layout to draw."""
    args = ["-e"]
    if file_path:
        p = Path(file_path).expanduser()
        if not p.is_file():
            raise RuntimeError(f"File not found: {p}")
        args.append(str(p))
    return f"KLayout editor launched: {_launch_app(args)}"


# ---------------------------------------------------------------------------
# Load / inspect existing layouts, and simple DRC
# ---------------------------------------------------------------------------
def _resolve_top(ly: db.Layout, top_cell: Optional[str]) -> db.Cell:
    if top_cell is not None:
        if not ly.has_cell(top_cell):
            names = [c.name for c in ly.each_cell()]
            raise RuntimeError(f"Cell '{top_cell}' not found. Cells: {names}")
        return ly.cell(ly.cell_by_name(top_cell))
    tops = ly.top_cells()
    if not tops:
        raise RuntimeError("Layout has no cells.")
    return tops[0]


def _region(ly: db.Layout, top: db.Cell, layer: int, datatype: int) -> db.Region:
    """Flattened region for a layer/datatype (empty if the layer is absent)."""
    li = ly.find_layer(layer, datatype)
    if li is None:
        return db.Region()
    return db.Region(top.begin_shapes_rec(li))


def _source(path: Optional[str], top_cell: Optional[str]) -> tuple[db.Layout, db.Cell]:
    """Resolve the layout to operate on: a file if given, else the session."""
    if path:
        p = Path(path).expanduser()
        if not p.is_file():
            raise RuntimeError(f"File not found: {p}")
        ly = db.Layout()
        ly.read(str(p))
        return ly, _resolve_top(ly, top_cell)
    s = _require_session()
    return s.layout, s.top


@mcp.tool()
def load_gds(path: str, top_cell: Optional[str] = None) -> str:
    """Load an existing GDS/OASIS file into the active session for editing.

    After loading, keep adding shapes (add_box / add_polygon / ...), inspect or
    DRC-check it, then save_gds() to write it back. ``top_cell`` selects the cell
    to edit (defaults to the first top cell). Replaces any current in-memory layout.
    """
    global _session
    p = Path(path).expanduser()
    if not p.is_file():
        raise RuntimeError(f"File not found: {p}")
    ly = db.Layout()
    ly.read(str(p))
    top = _resolve_top(ly, top_cell)
    _session = LayoutSession(layout=ly, top=top)
    nlayers = len(list(ly.layer_indexes()))
    return (
        f"Loaded {p}: top_cell='{top.name}', dbu={ly.dbu} um, "
        f"{ly.cells()} cells, {nlayers} layers. Ready to edit."
    )


@mcp.tool()
def inspect_gds(path: Optional[str] = None, top_cell: Optional[str] = None) -> str:
    """Inspect a layout: per-layer shape count, area and bbox, plus the cell list.

    With ``path``: inspect that file without touching the session. Without it:
    inspect the current in-memory session. Areas use merged geometry (so
    overlaps are not double-counted); coordinates are in micrometers.
    """
    ly, top = _source(path, top_cell)
    dbu = ly.dbu
    out = [
        f"top_cell='{top.name}', dbu={dbu} um, cells={ly.cells()}",
        f"bbox: {top.dbbox().to_s()} um",
        f"cells: {[c.name for c in ly.each_cell()]}",
        "",
        f"{'layer':<10}{'shapes':>8}{'area[um^2]':>14}   bbox[um]",
    ]
    idxs = sorted(ly.layer_indexes(), key=lambda i: (ly.get_info(i).layer, ly.get_info(i).datatype))
    if not idxs:
        out.append("(no layers)")
    for li in idxs:
        info = ly.get_info(li)
        reg = db.Region(top.begin_shapes_rec(li))
        n = reg.count()
        reg.merge()
        area = reg.area() * dbu * dbu
        bb = reg.bbox()
        bbs = (
            f"({bb.left * dbu:g},{bb.bottom * dbu:g})-({bb.right * dbu:g},{bb.top * dbu:g})"
            if not bb.empty()
            else "-"
        )
        out.append(f"{info.layer}/{info.datatype:<8}{n:>8}{area:>14.4f}   {bbs}")
    return "\n".join(out)


def _locations(obj, dbu: float, maxn: int) -> list[str]:
    """Centre points (um) of up to ``maxn`` violation markers (EdgePairs or Region)."""
    locs = []
    for i, item in enumerate(obj.each()):
        if i >= maxn:
            break
        b = item.bbox()
        cx = (b.left + b.right) / 2 * dbu
        cy = (b.bottom + b.top) / 2 * dbu
        locs.append(f"({cx:.3f},{cy:.3f})")
    return locs


def _check_rule(ly: db.Layout, top: db.Cell, rule: dict, max_report: int) -> str:
    dbu = ly.dbu
    rtype = rule.get("type", "")
    layer = int(rule["layer"])
    dt = int(rule.get("datatype", 0))
    reg = _region(ly, top, layer, dt)
    tag = f"{layer}/{dt}"

    def to_dbu(v) -> int:
        return round(float(v) / dbu)

    if rtype in ("spacing", "space"):
        res = reg.space_check(to_dbu(rule["min"]))
        head = f"spacing {tag} >= {rule['min']}um"
    elif rtype == "width":
        res = reg.width_check(to_dbu(rule["min"]))
        head = f"width {tag} >= {rule['min']}um"
    elif rtype in ("overlap", "no_overlap", "not_overlap"):
        reg2 = _region(ly, top, int(rule["layer2"]), int(rule.get("datatype2", 0)))
        inter = reg & reg2
        inter.merge()
        tag2 = f"{rule['layer2']}/{rule.get('datatype2', 0)}"
        n = inter.count()
        locs = _locations(inter, dbu, max_report)
        area = inter.area() * dbu * dbu
        status = "PASS" if n == 0 else f"FAIL ({n} regions, {area:.4f} um^2)"
        extra = f"  at {', '.join(locs)}" if locs else ""
        return f"forbidden overlap {tag} & {tag2}: {status}{extra}"
    elif rtype == "separation":
        reg2 = _region(ly, top, int(rule["layer2"]), int(rule.get("datatype2", 0)))
        res = reg.separation_check(reg2, to_dbu(rule["min"]))
        head = f"separation {tag} <-> {rule['layer2']}/{rule.get('datatype2', 0)} >= {rule['min']}um"
    elif rtype in ("enclosure", "enclosing"):
        reg2 = _region(ly, top, int(rule["layer2"]), int(rule.get("datatype2", 0)))
        # reg2 must enclose reg by at least min
        res = reg2.enclosing_check(reg, to_dbu(rule["min"]))
        head = f"enclosure {rule['layer2']}/{rule.get('datatype2', 0)} of {tag} >= {rule['min']}um"
    else:
        return f"unknown rule type: {rtype!r}"

    n = res.count()
    status = "PASS" if n == 0 else f"FAIL ({n} violations)"
    locs = _locations(res, dbu, max_report)
    extra = f"  at {', '.join(locs)}" if locs else ""
    return f"{head}: {status}{extra}"


@mcp.tool()
def drc_check(
    rules: list[dict],
    path: Optional[str] = None,
    top_cell: Optional[str] = None,
    max_report: int = 10,
) -> str:
    """Run simple DRC rules against a layout and report violations.

    Operates on ``path`` if given, else the current session. Each rule is a dict
    (datatype defaults to 0, distances in micrometers):

      {"type": "spacing",     "layer": L, "datatype": D, "min": um}
      {"type": "width",       "layer": L, "datatype": D, "min": um}
      {"type": "overlap",     "layer": L, "datatype": D, "layer2": L2, "datatype2": D2}
      {"type": "separation",  "layer": L, "datatype": D, "layer2": L2, "datatype2": D2, "min": um}
      {"type": "enclosure",   "layer": L, "datatype": D, "layer2": L2, "datatype2": D2, "min": um}

    "spacing" is min space within a layer; "width" is min feature width;
    "overlap" flags any intersection between two layers (forbidden overlap);
    "separation" is min space between two layers; "enclosure" requires layer2 to
    surround layer by min. Up to ``max_report`` violation centres are listed per rule.
    """
    if not rules:
        return "No rules provided."
    ly, top = _source(path, top_cell)
    lines, fails = [], 0
    for rule in rules:
        try:
            line = _check_rule(ly, top, rule, max_report)
        except Exception as e:  # noqa: BLE001
            line = f"rule {rule}: ERROR {type(e).__name__}: {e}"
        if ": FAIL" in line or line.startswith(("unknown", "rule ")):
            fails += 1
        lines.append(line)
    summary = f"DRC: {len(rules)} rules, {fails} failing\n" + "\n".join(lines)
    return summary


# ---------------------------------------------------------------------------
# Escape hatch: arbitrary klayout.db scripting
# ---------------------------------------------------------------------------
@mcp.tool()
def run_script(code: str) -> str:
    """Execute Python with ``klayout.db`` available (advanced).

    Injected names: ``db`` (klayout.db), ``klayout``, ``session`` (current
    LayoutSession or None), ``LayoutSession``. stdout is captured and returned.
    A script may rebind ``session`` to a new LayoutSession to make it the active
    layout. Runs locally in-process with full Python access.
    """
    global _session
    ns: dict = {
        "db": db,
        "klayout": klayout,
        "session": _session,
        "LayoutSession": LayoutSession,
    }
    buf = io.StringIO()
    try:
        with redirect_stdout(buf):
            exec(code, ns)  # noqa: S102 - intentional local scripting tool
    except Exception as e:  # noqa: BLE001
        return f"ERROR: {type(e).__name__}: {e}\n--- stdout ---\n{buf.getvalue()}"
    if isinstance(ns.get("session"), LayoutSession):
        _session = ns["session"]
    out = buf.getvalue().strip()
    return f"OK\n{out}" if out else "OK"


def main() -> None:
    mcp.run()


if __name__ == "__main__":
    main()
