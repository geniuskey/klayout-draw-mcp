# klayout-draw-mcp

An [MCP](https://modelcontextprotocol.io) server for **drawing GDS layouts** with **KLayout** — generate, edit, and view layouts from an AI assistant such as Claude Code or Claude Desktop.

Layout geometry is built in-process with the standalone [`klayout`](https://pypi.org/project/klayout/) Python module (no GUI needed). The installed KLayout application is launched only for viewing or manual editing.

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
| `add_via(x, y, bottom_layer, top_layer, cut_layer, …)` | Via: cut array + enclosing metal |
| `add_wire(layer, points, width)` | Manhattan wire (auto L-corners) |
| `layout_info()` | Inspect current layout (layers, bbox, shape count) |
| `load_gds(path, top_cell?)` | Load an existing GDS/OASIS into the session for editing |
| `inspect_gds(path?)` | Per-layer shape count, area and bbox of a file or the session |
| `drc_check(rules, path?)` | Simple DRC: spacing / width / overlap / separation / enclosure |
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
claude mcp add klayout -s user -- "<repo>/.venv/Scripts/python.exe" -m klayout_draw_mcp.server
```

On macOS/Linux use `.venv/bin/python`.

## Usage

> "Draw a 5×5 µm box on layer 1 and a 2 µm-wide path, then save to out.gds and open it."

Claude calls `new_layout` → `add_box` / `add_path` → `save_gds(open_after=True)`.

You can also open and check an existing layout:

> "Load chip.gds, check that M1 spacing ≥ 0.15 µm and that OD never overlaps POLY, and report violations."

Claude calls `load_gds` → `inspect_gds` → `drc_check([...])`, then edits and `save_gds`.
See [Editing &amp; DRC](https://geniuskey.github.io/klayout-draw-mcp/editing-and-drc/).

For anything beyond the basic shapes, `run_script` exposes the full `klayout.db` API.

## Examples

Self-contained scripts in [`examples/`](examples). Each builds a layout with the
standalone `klayout.db` module and writes a GDS:

```bash
uv run python examples/cis_aps_pixel.py out.gds
```

You can also paste the body of a script's `build()` function into the `run_script`
tool. The scripts share one layer map (OD 3/0, POLY 6/0, NPLUS 4/0, METAL1 9/0, ...).

| Example | What it draws |
| --- | --- |
| `basic_shapes.py` | The four primitives: box, path, polygon, label |
| `nmos_transistor.py` | A single NMOS (active, poly gate, n+, contacts, M1 S/G/D) |
| `cmos_inverter.py` | A CMOS inverter: PMOS over NMOS, shared gate, Vdd/Vss rails |
| `cis_aps_pixel.py` | A 1 µm 4T CMOS image-sensor pixel, tiled as a 2×2 array |

## Place &amp; route skill

`skills/klayout-pnr/` packages place-and-route recipes — row placement, power rails, and
an obstacle-aware maze (Lee) router — plus a `SKILL.md` workflow guide for assistants.
Copy it to your skills directory to have it auto-discovered:

```bash
cp -r skills/klayout-pnr ~/.claude/skills/
```

## Documentation

Full docs (Getting Started walkthrough, examples, editing/DRC, place &amp; route) are at
**https://geniuskey.github.io/klayout-draw-mcp/**.

## Note

`run_script` executes arbitrary Python locally, in-process. Only run scripts you trust.
