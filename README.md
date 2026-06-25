# klayout-mcp

An [MCP](https://modelcontextprotocol.io) server for **KLayout** — draw, generate, and view GDS layouts from an AI assistant such as Claude Code or Claude Desktop.

Layout geometry is built in-process with the standalone [`klayout`](https://pypi.org/project/klayout/) Python module (no GUI needed). The installed KLayout application is launched only for viewing or manual editing.

## Tools

| Tool | Purpose |
| --- | --- |
| `new_layout(top_cell, dbu)` | Start a new in-memory layout (coordinates in micrometers) |
| `add_box(layer, x1, y1, x2, y2, datatype)` | Add a rectangle |
| `add_polygon(layer, points, datatype)` | Add a polygon from `[x, y]` vertices |
| `add_path(layer, points, width, datatype)` | Add a path with width |
| `add_label(layer, x, y, text, datatype)` | Add a text label |
| `layout_info()` | Inspect current layout (layers, bbox, shape count) |
| `save_gds(path, open_after)` | Write GDS/OASIS; optionally open in the editor |
| `open_layout(file_path)` | Open a file in KLayout (viewer) |
| `open_editor(file_path?)` | Open KLayout in editor mode, or a blank layout |
| `run_script(code)` | Run arbitrary Python with `klayout.db` (cell hierarchy, arrays, booleans, DRC, ...) |

## Requirements

- Python ≥ 3.10
- The `klayout` and `mcp` Python packages (installed via the steps below)
- The [KLayout application](https://www.klayout.de/build.html) — only needed for `open_layout` / `open_editor`

## Install

```bash
uv sync
```

## Register with Claude Code

```bash
claude mcp add klayout -s user -- "<repo>/.venv/Scripts/python.exe" -m klayout_mcp.server
```

On macOS/Linux use `.venv/bin/python`.

## Usage

> "Draw a 5×5 µm box on layer 1 and a 2 µm-wide path, then save to out.gds and open it."

Claude calls `new_layout` → `add_box` / `add_path` → `save_gds(open_after=True)`.

For anything beyond the basic shapes, `run_script` exposes the full `klayout.db` API.

## Note

`run_script` executes arbitrary Python locally, in-process. Only run scripts you trust.
