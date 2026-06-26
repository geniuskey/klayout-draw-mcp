# Live Editing the Open KLayout Window

The drawing tools and `run_script` all work on an **in-process** layout: the server
builds geometry with the standalone `klayout.db` module, writes a file, and the GUI is
only ever *launched* to view the result. There is no way back into a running KLayout from
those tools — so if you already have a layout open in KLayout and ask for a change, the
assistant can only regenerate a file and reload it.

The **live bridge** closes that gap. A small macro runs *inside* your KLayout window and
opens a loopback TCP listener; the server's `gui_exec` / `gui_info` tools connect to it and
run Python against the layout you actually have open, editing it in place and redrawing.

```
┌──────────────┐   gui_exec(code)    ┌────────────────────────────┐
│ MCP server   │ ──────────────────▶ │ KLayout GUI                │
│ (klayout.db) │   TCP 127.0.0.1     │  mcp_live_bridge.py macro  │
│              │ ◀────────────────── │  exec on main thread (pya) │
└──────────────┘   stdout / error    └────────────────────────────┘
```

!!! warning
    The bridge executes arbitrary Python **inside your KLayout application**. It binds to
    `127.0.0.1` (loopback) only. Run it on a machine you trust and don't expose the port.

## 1. Start the bridge inside KLayout

1. Open KLayout (the GUI application) and load the layout you want to edit.
2. Open the Macro Development IDE (**F5**, or *Tools → Macro Development*).
3. Create a new **Python** macro, paste in the bridge source, and **Run** it (▶).

To get the source, just ask the assistant — it calls the **`gui_bridge_macro()`** tool and
prints the whole macro for you to paste. (It ships with the package as
[`klayout_draw_mcp/mcp_live_bridge.py`](https://github.com/geniuskey/klayout-draw-mcp/blob/main/src/klayout_draw_mcp/mcp_live_bridge.py),
so there is nothing extra to download.)

You should see in the macro console:

```
[mcp_live_bridge] listening on 127.0.0.1:8082
[mcp_live_bridge] ready - the klayout-draw-mcp gui_exec tool can now connect
```

Alternatively, launch KLayout with the macro file and a layout in one go:

```bash
klayout -rm /path/to/mcp_live_bridge.py my_layout.gds
```

The listener keeps running for the life of the window; you only start it once per session.

## 2. Edit from the assistant

With the bridge running, ask for changes to the **open** layout. The assistant uses:

- **`gui_bridge_macro()`** — returns the macro source to paste into KLayout (step 1 above).
- **`gui_info()`** — confirm the bridge is reachable and report the active cell, dbu, layers
  and bbox of the layout currently open in KLayout.
- **`gui_exec(code)`** — run Python on KLayout's main thread against the visible layout.

`gui_exec` injects these names (note GUI Python is **`pya`**, not `klayout.db`):

| Name | What it is |
| --- | --- |
| `pya` | The KLayout GUI Python module |
| `view` | The current `pya.LayoutView` (or `None`) |
| `cv` | The active `pya.CellView` |
| `layout` | The current `pya.Layout` — coordinates in micrometers via `DBox`/`DPoint` |
| `cell` | The currently shown `pya.Cell` (the `add_*` target) |
| `refresh()` | Redraw the view (also called automatically after every call) |

Variables you set persist between calls. Examples:

```python
# Add a 5x5 um box on layer 1/0 to the open cell
cell.shapes(layout.layer(1, 0)).insert(pya.DBox(0, 0, 5, 5))
```

```python
# Move every shape on layer 2/0 up by 1 um
li = layout.layer(2, 0)
shapes = cell.shapes(li)
for s in list(shapes.each()):
    shapes.transform(s, pya.DTrans(pya.DVector(0, 1)))
```

```python
# Delete a layer's geometry entirely
cell.shapes(layout.layer(10, 0)).clear()
```

The change appears in the KLayout window immediately — no save-and-reload round trip.

## 3. Saving

The bridge edits the in-memory layout shown in the window, exactly as if you had drawn by
hand. Save from KLayout (**Ctrl+S** / *File → Save*), or from the assistant:

```python
layout.write("/path/to/out.gds")
```

## When to use which

| You want to… | Use |
| --- | --- |
| Generate a layout from scratch, then view it | drawing tools / `run_script` → `save_gds(open_after=True)` |
| Edit a file on disk and write it back | `load_gds` → edit → `save_gds` |
| **Edit the layout already open in KLayout, live** | **`gui_exec` / `gui_info`** (this page) |

## Troubleshooting

| Symptom | Fix |
| --- | --- |
| `Could not reach the KLayout live bridge` | The macro isn't running. Get the source via `gui_bridge_macro()`, paste it into KLayout and Run (F5). Check the console shows it listening on `127.0.0.1:8082`. |
| `No layout is open in KLayout.` | The bridge is up but no layout is loaded in the active view. Open a file in KLayout first. |
| Port already in use | Another bridge (or process) holds `8082`. Edit `PORT` at the top of the macro, then pass the same `port=` to `gui_exec`/`gui_info`. |
| Edits don't appear | Call `refresh()` at the end of your snippet (normally automatic). Make sure you edited `cell`/`layout` from the bridge, not the in-process session. |
