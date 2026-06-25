# Tool Reference

Every MCP tool the server exposes, generated from its source. All coordinates are in
micrometers; the database grid defaults to `dbu = 0.001` (1 nm).

## Drawing

::: klayout_draw_mcp.server
    options:
      members:
        - new_layout
        - add_box
        - add_polygon
        - add_path
        - add_label

## Cells, placement & routing

::: klayout_draw_mcp.server
    options:
      members:
        - create_cell
        - use_cell
        - place_cell
        - add_via
        - add_wire

## Inspect & DRC

::: klayout_draw_mcp.server
    options:
      members:
        - layout_info
        - load_gds
        - inspect_gds
        - drc_check

## Save & view

::: klayout_draw_mcp.server
    options:
      members:
        - save_gds
        - open_layout
        - open_editor

## Scripting

::: klayout_draw_mcp.server
    options:
      members:
        - run_script
