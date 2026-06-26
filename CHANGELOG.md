# Changelog

All notable changes to this project are documented here. The format is based on
[Keep a Changelog](https://keepachangelog.com/), and this project adheres to
[Semantic Versioning](https://semver.org/).

## [0.2.0] - 2026-06-26

### Added
- Live GUI bridge: edit the layout **already open** in a running KLayout window instead of
  regenerating and reloading a file. A macro (`mcp_live_bridge.py`, shipped with the package)
  runs inside KLayout and exposes a loopback TCP listener; new tools `gui_exec` (run Python
  against the visible `pya` layout, on the GUI main thread) and `gui_info` (inspect the open
  layout) drive it, and `gui_bridge_macro` returns the macro source to paste into KLayout.
- Documentation: a Live Editing page, plus an OpenCode MCP setup guide in Installation.

## [0.1.2] - 2026-06-26

### Added
- Placement & routing building blocks: `create_cell`, `use_cell`, `place_cell`
  (instance or array), `add_via` (cut array + enclosing metal), and `add_wire`
  (Manhattan, auto L-corners). Drawing tools now target a switchable active cell.
- `klayout-pnr` skill with recipes — row placement, power rails, and an obstacle-aware
  maze (Lee) router — plus an end-to-end place-and-route demo.
- Documentation: Installation, Getting Started, Placement & Routing, an auto-generated
  Tool Reference, and a `run_script` cookbook — with rendered screenshots, a DRC
  violation visualisation, and a layer colour legend.

## [0.1.1] - 2026-06-25

### Added
- `load_gds(path, top_cell?)` — load an existing GDS/OASIS file into the session for editing.
- `inspect_gds(path?)` — per-layer shape count, merged area and bbox, plus the cell list,
  for a file or the current session.
- `drc_check(rules, path?)` — simple DRC: `spacing`, `width`, `overlap`, `separation` and
  `enclosure` rules, reporting violation counts and locations.
- Documentation page covering the editing and DRC workflow.

## [0.1.0] - 2026-06-25

### Added
- Initial MCP server with drawing tools: `new_layout`, `add_box`, `add_polygon`,
  `add_path`, `add_label`, `layout_info`, `save_gds`, `open_layout`, `open_editor`,
  and the `run_script` escape hatch for the full `klayout.db` API.
- Example gallery: basic shapes, NMOS transistor, CMOS inverter, and a 1 µm 4T CIS APS
  pixel tiled as a 2×2 array, with headless screenshot rendering.
- MkDocs Material documentation site.
- GitHub Actions for building/deploying the docs to GitHub Pages and for publishing to
  PyPI via Trusted Publishing.

[0.2.0]: https://pypi.org/project/klayout-draw-mcp/0.2.0/
[0.1.2]: https://pypi.org/project/klayout-draw-mcp/0.1.2/
[0.1.1]: https://pypi.org/project/klayout-draw-mcp/0.1.1/
[0.1.0]: https://pypi.org/project/klayout-draw-mcp/0.1.0/
