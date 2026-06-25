---
name: klayout-pnr
description: Use when doing placement and metal routing (manual or automatic) on GDS layouts via the klayout-draw-mcp MCP server — standard-cell rows, multi-layer wires, vias, and obstacle-aware maze (Lee) routing, with DRC checking in the loop.
---

# KLayout Place & Route

This is **not** a P&R engine. It is a set of techniques for driving the
`klayout-draw-mcp` tools to do placement and routing well. The division of labour:
**you (the agent) plan** the floorplan, net list and routing order; **the server
realises geometry and checks DRC**. Iterate: route → `drc_check` → fix → repeat.

## When to use

- Placing cells (standard-cell rows, arrays, abutment)
- Metal routing: multi-layer wires + vias, power rails
- Automatic routing: connecting a net list while avoiding obstacles

## Workflow

1. **Start**: `new_layout(top_cell, dbu=0.001)` or `load_gds(path)` to edit existing.
2. **Define library cells**: `create_cell("NAND2")` → `add_box`/`add_polygon`/`add_via`
   build it → `use_cell(top)` to return. (Or `load_gds` a cell library.)
3. **Place**: `place_cell(cell, x, y, orient, nx, ny, dx, dy)`. For rows, compute
   positions with the `place_rows` recipe, then one `place_cell` per placement.
4. **Route**: `add_wire(layer, points, width)` for known paths (auto-inserts Manhattan
   corners) and `add_via(...)` at layer changes. For many nets / obstacle avoidance,
   use the **maze router** below inside `run_script`.
5. **Check**: `drc_check([...])` — read the violation locations, adjust, re-run.
6. **Save**: `save_gds(path, open_after=True)`.

## Tools vs. run_script

- **Few shapes / known geometry** → call the MCP tools directly (`place_cell`,
  `add_wire`, `add_via`). Coordinates are micrometers; keep them on your routing grid.
- **Automatic placement/routing over many nets** → use `run_script`: build the layout
  programmatically with `klayout.db` and the recipes here, then `save_gds`.

## Layer & grid conventions

| Name | layer/dt | Use |
| --- | --- | --- |
| OD `3/0`, POLY `6/0` | | device layers |
| M1 `9/0`, VIA1 `11/0`, M2 `12/0` | | routing stack |
| PWR `90/0` | | power rails |
| BLOCK `200/0` | | routing blockage / debug marker |

Pick one **routing pitch** (e.g. 0.2 µm) and keep pins and wires on multiples of it.
Convention: route M1 horizontal, M2 vertical, switch layers with a via at the turn.

## Recipes

Standalone, tested scripts live in `scripts/` (run `uv run python
skills/klayout-pnr/scripts/demo_pnr.py out.gds` for a full place + route demo):

- `pnr_helpers.py` — layer map, `draw_box/draw_wire/draw_via`, `RoutingGrid`
- `placer.py` — `place_rows`, `power_rails`
- `maze_router.py` — `lee`, `route_net` (obstacle-aware shortest path)
- `demo_pnr.py` — ties it together: 6 cells in 2 rows, 5 nets routed around the cells

### Row placement

```python
from placer import place_rows
placements = place_rows(
    cells=[("NAND2", 2.0), ("INV", 1.0), ("NAND2", 2.0), ("INV", 1.0)],
    row_width=4.0, row_pitch=4.0, flip_alt=True,
)
# each: {"name","x","y","orient","row"} -> feed to place_cell(...)
```

### Auto routing (maze / Lee) — paste into run_script

`run_script` injects `session` and `db`. This self-contained block routes a net list
on a grid, avoiding cell footprints and previously-routed nets:

```python
import heapq
ly, top = session.layout, session.top
M1 = session.layer(9, 0)
PITCH = 0.2

def node(x, y): return (round(x / PITCH), round(y / PITCH))
def point(c, r): return (c * PITCH, r * PITCH)

DIRS = ((1, 0), (-1, 0), (0, 1), (0, -1))
def lee(nx, ny, blocked, start, goal, turn=0.6):
    if start == goal: return [start]
    pq = [(0.0, start, -1)]; best = {(start, -1): 0.0}; parent = {}
    while pq:
        cost, cur, cd = heapq.heappop(pq)
        if cur == goal:
            path = [cur]; key = (cur, cd)
            while key in parent: key = parent[key]; path.append(key[0])
            return path[::-1]
        for di, (dc, dr) in enumerate(DIRS):
            nc, nr = cur[0] + dc, cur[1] + dr; nxt = (nc, nr)
            if not (0 <= nc < nx and 0 <= nr < ny): continue
            if nxt in blocked and nxt != goal: continue
            nco = cost + 1.0 + (turn if cd != -1 and di != cd else 0.0)
            k = (nxt, di)
            if nco < best.get(k, 1e18):
                best[k] = nco; parent[k] = (cur, cd); heapq.heappush(pq, (nco, nxt, di))
    return None

def route(nx, ny, blocked, p1, p2, width=0.15):
    s, g = node(*p1), node(*p2); blocked.discard(s); blocked.discard(g)
    path = lee(nx, ny, blocked, s, g)
    if path is None: return False
    for n in path: blocked.add(n)
    # compress collinear, then draw as a Manhattan path
    pts = [path[0]]
    for i in range(1, len(path) - 1):
        if (path[i][0]-path[i-1][0], path[i][1]-path[i-1][1]) != (path[i+1][0]-path[i][0], path[i+1][1]-path[i][1]):
            pts.append(path[i])
    pts.append(path[-1])
    dpts = [db.DPoint(*point(*n)) for n in pts]; dpts[0] = db.DPoint(*p1); dpts[-1] = db.DPoint(*p2)
    top.shapes(M1).insert(db.DPath(dpts, width)); return True

# 1) mark obstacles: grid nodes inside cell footprints (and keep pins free)
GX, GY = 40, 40
blocked = set()
def block_box(x1, y1, x2, y2):
    for c in range(round(x1/PITCH), round(x2/PITCH)):
        for r in range(round(y1/PITCH), round(y2/PITCH)):
            blocked.add((c, r))
# block_box(...) for each placed cell footprint

# 2) route nets in a sensible order (congested / long nets first)
nets = [((1.5, 2.0), (3.0, 2.0))]  # list of (pin_a, pin_b) in um
for a, b in nets:
    if not route(GX, GY, blocked, a, b):
        print("UNROUTED", a, b)
```

After routing, run `drc_check` (spacing on M1, separation between nets) and re-route any
failures, or rip up and reorder nets.

## DRC loop

```text
drc_check([
  {"type":"spacing", "layer":9, "min":0.2},      # M1 spacing
  {"type":"width",   "layer":9, "min":0.1},       # M1 width
  {"type":"overlap", "layer":9, "layer2":6}       # M1 must not sit on POLY
])
```

Violation locations come back as centre points — move the offending wire/cell with the
drawing tools and re-check.

## Common pitfalls

- **Off-grid coordinates** — snap pins and wire points to the routing pitch, or the
  maze nodes won't line up with geometry.
- **Pins reported as blocked** — exclude the start/goal nodes from the blockage set
  (the recipe does `blocked.discard(...)`).
- **Net ordering matters** — this is greedy with no rip-up; route congested/long nets
  first, and reorder if a later net is blocked.
- **Manhattan only** — `add_wire` and the router emit axis-aligned segments; don't expect
  45°.
- **Layer changes need a via** — drop `add_via` at the point where a route switches metal.

## Install

Copy this folder to your skills directory so the assistant discovers it:

```bash
cp -r skills/klayout-pnr ~/.claude/skills/      # user-wide
# or .claude/skills/ inside a project
```

The `scripts/` recipes are usable standalone (`python scripts/demo_pnr.py`) or by pasting
their functions into the `run_script` MCP tool.
