"""Obstacle-aware maze (Lee) routing on a grid — the core auto-routing technique.

A breadth-first Lee expansion finds a shortest Manhattan path between two grid nodes
while avoiding blocked nodes (other nets, cell footprints). ``route_net`` routes one
net and marks its path as blocked so later nets avoid it (greedy, no rip-up). A turn
penalty (Dijkstra) is used so paths prefer straight runs with fewer jogs.
"""

from __future__ import annotations

import heapq

_DIRS = ((1, 0), (-1, 0), (0, 1), (0, -1))


def lee(nx: int, ny: int, blocked: set, start, goal, turn_cost: float = 0.6):
    """Shortest grid path start->goal avoiding ``blocked`` (4-neighbour).

    Returns a list of (col, row) nodes inclusive, or None if unreachable.
    A small ``turn_cost`` per direction change yields fewer corners.
    """
    if start == goal:
        return [start]
    # state: (cost, node, came_dir); came_dir index into _DIRS or -1
    pq = [(0.0, start, -1)]
    best = {(start, -1): 0.0}
    parent = {}
    while pq:
        cost, cur, cdir = heapq.heappop(pq)
        if cur == goal:
            path = [cur]
            key = (cur, cdir)
            while key in parent:
                key = parent[key]
                path.append(key[0])
            path.reverse()
            return path
        for di, (dc, dr) in enumerate(_DIRS):
            nc, nr = cur[0] + dc, cur[1] + dr
            nxt = (nc, nr)
            if not (0 <= nc < nx and 0 <= nr < ny):
                continue
            if nxt in blocked and nxt != goal:
                continue
            step = 1.0 + (turn_cost if (cdir != -1 and di != cdir) else 0.0)
            nkey = (nxt, di)
            ncost = cost + step
            if ncost < best.get(nkey, float("inf")):
                best[nkey] = ncost
                parent[nkey] = (cur, cdir)
                heapq.heappush(pq, (ncost, nxt, di))
    return None


def compress(path):
    """Drop collinear interior nodes, keeping only corners and endpoints."""
    if not path or len(path) < 3:
        return path
    out = [path[0]]
    for i in range(1, len(path) - 1):
        ax, ay = path[i - 1]
        bx, by = path[i]
        cx, cy = path[i + 1]
        if (bx - ax, by - ay) != (cx - bx, cy - by):
            out.append(path[i])
    out.append(path[-1])
    return out


def route_net(grid, blocked: set, p1, p2):
    """Route p1->p2 (micrometers) on ``grid`` avoiding ``blocked`` grid nodes.

    On success returns Manhattan corner points in micrometers (endpoints exact) and
    adds the routed nodes to ``blocked``. Returns None if no path exists.
    """
    s = grid.node(*p1)
    g = grid.node(*p2)
    blocked.discard(s)
    blocked.discard(g)
    path = lee(grid.nx, grid.ny, blocked, s, g)
    if path is None:
        return None
    for n in path:
        blocked.add(n)
    pts = [grid.point(*n) for n in compress(path)]
    pts[0] = (float(p1[0]), float(p1[1]))
    pts[-1] = (float(p2[0]), float(p2[1]))
    return pts
