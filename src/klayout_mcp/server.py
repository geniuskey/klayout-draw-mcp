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
