# klayout-draw-mcp

[![PyPI](https://img.shields.io/pypi/v/klayout-draw-mcp.svg)](https://pypi.org/project/klayout-draw-mcp/)
[![Python](https://img.shields.io/pypi/pyversions/klayout-draw-mcp.svg)](https://pypi.org/project/klayout-draw-mcp/)
[![License: MIT](https://img.shields.io/badge/license-MIT-green.svg)](https://github.com/geniuskey/klayout-draw-mcp/blob/main/LICENSE)

An [MCP](https://modelcontextprotocol.io) server for **drawing GDS layouts** with
**[KLayout](https://www.klayout.de)** — generate, edit and view chip layouts straight
from an AI assistant such as Claude Code or Claude Desktop.

Layout geometry is built in-process with the standalone
[`klayout`](https://pypi.org/project/klayout/) Python module — no GUI needed. The
installed KLayout application is launched only when you want to view or hand-edit a
result.

> "Draw a CIS 4T APS pixel at 1 µm pitch, tile it 2×2, then save to `out.gds` and open it."

The assistant calls `new_layout` → drawing tools / `run_script` → `save_gds(open_after=True)`.
See the [Examples](examples.md) for layouts produced exactly this way.

## Tools

| Tool | Purpose |
| --- | --- |
| `new_layout(top_cell, dbu)` | Start a new in-memory layout (coordinates in micrometers) |
| `add_box(layer, x1, y1, x2, y2, datatype)` | Add a rectangle |
| `add_polygon(layer, points, datatype)` | Add a polygon from `[x, y]` vertices |
| `add_path(layer, points, width, datatype)` | Add a path with width |
| `add_label(layer, x, y, text, datatype)` | Add a text label |
| `create_cell(name)` / `use_cell(name)` | Create/select the active drawing cell |
| `place_cell(cell, x, y, orient, nx, ny, dx, dy)` | Place an instance or array of a cell |
| `add_via(x, y, bottom_layer, top_layer, cut_layer, …)` | Via: cut array + enclosing metal on two layers |
| `add_wire(layer, points, width)` | Manhattan wire (auto-inserts L-corners) |
| `layout_info()` | Inspect current layout (layers, bbox, shape count) |
| `load_gds(path, top_cell?)` | Load an existing GDS/OASIS into the session for editing |
| `inspect_gds(path?)` | Per-layer shape count, area and bbox of a file or the session |
| `drc_check(rules, path?)` | Simple DRC: spacing / width / overlap / separation / enclosure |
| `save_gds(path, open_after)` | Write GDS/OASIS; optionally open in the editor |
| `open_layout(file_path)` | Open a file in KLayout (viewer) |
| `open_editor(file_path?)` | Open KLayout in editor mode, or a blank layout |
| `run_script(code)` | Run arbitrary Python with `klayout.db` (cell hierarchy, arrays, booleans, DRC, …) |

## Install

```bash
pip install klayout-draw-mcp
```

The [KLayout application](https://www.klayout.de/build.html) is only required for
`open_layout` / `open_editor`.

## Register with Claude Code

```bash
claude mcp add klayout -s user -- python -m klayout_draw_mcp.server
```

When running from a checkout, point at the project's interpreter instead, e.g.
`<repo>/.venv/Scripts/python.exe` on Windows or `<repo>/.venv/bin/python` on macOS/Linux.

For `uvx`, Claude Desktop, verification and troubleshooting, see the full
[Installation &amp; Setup](installation.md) guide.

## How it works

There are two complementary ways to produce geometry:

1. **High-level drawing tools** (`new_layout`, `add_box`, `add_polygon`, …) build a
   layout step by step. All coordinates are in micrometers.
2. **`run_script`** executes arbitrary Python with `klayout.db` available, for anything
   the high-level tools do not cover — cell hierarchy, array instances, boolean ops, DRC.
   See the [run_script cookbook](run-script.md) for copy-paste recipes.

Beyond drawing from scratch, you can **load an existing layout** with `load_gds` and
keep editing it, **inspect** any file or the session with `inspect_gds`, and run
**simple DRC** with `drc_check` — spacing, width, forbidden overlap, separation and
enclosure rules, each violation reported with a location:

```json
[
  {"type": "spacing", "layer": 3, "datatype": 0, "min": 0.15},
  {"type": "width",   "layer": 6, "datatype": 0, "min": 0.08},
  {"type": "overlap", "layer": 3, "layer2": 6}
]
```

!!! warning
    `run_script` executes arbitrary Python locally, in-process. Only run scripts you trust.
