# `run_script` Cookbook

`run_script` executes Python in-process with these names injected: `db`
(`klayout.db`), `klayout`, `session` (the current `LayoutSession`, or `None`), and
`LayoutSession`. It is the escape hatch for anything the high-level tools don't cover —
boolean layer ops, sizing, hierarchy, connectivity, custom DRC. A script may rebind
`session` to a new `LayoutSession` to make it active. `stdout` is returned.

!!! warning
    `run_script` runs arbitrary Python locally, in-process. Only run scripts you trust.

All recipes below assume an active layout (`new_layout` or `load_gds` first) and use this
helper to pull a flattened [`Region`](https://www.klayout.de/doc-qt5/code/class_Region.html)
for a layer:

```python
ly, top = session.layout, session.top
dbu = ly.dbu
def R(layer, datatype=0):
    return db.Region(top.begin_shapes_rec(session.layer(layer, datatype)))
```

## Boolean operations

Derive layers with `&` (AND), `|` (OR), `-` (NOT), `^` (XOR):

```python
od, poly = R(3), R(6)
gate = od & poly          # transistor gate = OD AND POLY
sd = od - poly            # source/drain = OD NOT POLY
top.shapes(session.layer(20, 0)).insert(gate)
print("gate area um^2:", gate.area() * dbu * dbu)
```

## Grow / shrink (sizing)

`Region.sized(d)` oversizes by `d` database units (negative shrinks). Useful for
enclosure and spacing checks:

```python
grown = R(9).sized(round(0.1 / dbu))      # oversize M1 by 0.1 um
shrunk = R(3).sized(round(-0.05 / dbu))   # undersize OD by 0.05 um
top.shapes(session.layer(21, 0)).insert(grown)
```

## Merge / flatten a layer

```python
reg = R(9)
reg.merge()                                # union overlapping shapes
top.shapes(session.layer(9, 0)).clear()    # replace the layer with the merged result
top.shapes(session.layer(9, 0)).insert(reg)
```

## Cell hierarchy and arrays

Build a sub-cell once and instance it as an array (much smaller than flat copies):

```python
tile = ly.create_cell("TILE")
tile.shapes(session.layer(9, 0)).insert(db.DBox(0, 0, 0.5, 0.5))
top.insert(db.DCellInstArray(
    tile.cell_index(), db.DTrans(db.DVector(5, 0)),
    db.DVector(1, 0), db.DVector(0, 1), 3, 3))   # 3x3 array at 1 um pitch
```

## Custom DRC with violation markers

Draw spacing/width violations onto a marker layer so they're visible in the viewer
(this is exactly how the [Editing &amp; DRC](editing-and-drc.md) screenshot is made):

```python
mk = session.layer(200, 0)
for ep in R(9).space_check(round(0.2 / dbu)).each():   # M1 spacing < 0.2 um
    top.shapes(mk).insert(ep.bbox().enlarged(round(0.05 / dbu)))
```

`Region` also offers `width_check`, `separation_check`, `enclosing_check`, `overlap_check`
— the same primitives the `drc_check` tool wraps.

## Copy or move shapes between layers

```python
dst = top.shapes(session.layer(30, 0))
for sh in top.shapes(session.layer(9, 0)).each():
    dst.insert(sh)                               # copy M1 -> 30/0
# top.shapes(session.layer(9, 0)).clear()        # ...uncomment to move instead
```

## Measure area and counts

```python
for layer, dt in [(3, 0), (6, 0), (9, 0)]:
    reg = R(layer, dt); reg.merge()
    print(f"{layer}/{dt}: {reg.count()} polys, {reg.area() * dbu * dbu:.3f} um^2")
```

## Start a fresh layout from a script

Rebind `session` to make a new layout active, then keep using the high-level tools:

```python
session = LayoutSession.create("CHIP", 0.001)
session.top.shapes(session.layer(1, 0)).insert(db.DBox(0, 0, 10, 10))
```

For connectivity (opens/shorts) and netlist extraction, see KLayout's
[`LayoutToNetlist`](https://www.klayout.de/doc-qt5/code/class_LayoutToNetlist.html).
