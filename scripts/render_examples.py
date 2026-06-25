"""Render every example layout to a PNG for the documentation site.

Uses the headless KLayout ``klayout.lay`` renderer (no GUI), so it runs in CI.
Each ``examples/*.py`` exposes a ``build()`` returning a ``klayout.db.Layout``;
that layout is written to a temp GDS, loaded into an off-screen LayoutView and
saved as ``docs/assets/images/<name>.png``.

    uv run python scripts/render_examples.py
"""

from __future__ import annotations

import importlib.util
import tempfile
from pathlib import Path

import klayout.db as db
import klayout.lay as lay

ROOT = Path(__file__).resolve().parent.parent
EXAMPLES = ROOT / "examples"
OUT = ROOT / "docs" / "assets" / "images"

# Extra build() scripts outside examples/ to render for the docs.
EXTRA = [ROOT / "skills" / "klayout-pnr" / "scripts" / "demo_pnr.py"]

WIDTH, HEIGHT = 960, 720
MARGIN = 0.08  # fraction of the layout size added around the view


def load_build(path: Path):
    spec = importlib.util.spec_from_file_location(path.stem, path)
    mod = importlib.util.module_from_spec(spec)
    assert spec and spec.loader
    spec.loader.exec_module(mod)
    return mod.build


def render(gds: str, png: str) -> None:
    lv = lay.LayoutView()
    lv.load_layout(gds, 0)
    lv.max_hier()
    lv.zoom_fit()
    b = lv.box()
    m = max(b.width(), b.height()) * MARGIN
    lv.zoom_box(db.DBox(b.left - m, b.bottom - m, b.right + m, b.top + m))
    lv.save_image(png, WIDTH, HEIGHT)


def gs_layouts() -> dict:
    """Small layouts for the Getting Started page (built inline, no example file)."""
    res = {}
    # step 1: a single 5x5 um box on layer 1
    ly = db.Layout()
    ly.dbu = 0.001
    c = ly.create_cell("BOX")
    c.shapes(ly.layer(1, 0)).insert(db.DBox(0, 0, 5, 5))
    res["gs_box"] = ly
    # step 2: edit -> add a second box on layer 2 and a label
    ly = db.Layout()
    ly.dbu = 0.001
    c = ly.create_cell("BOX")
    c.shapes(ly.layer(1, 0)).insert(db.DBox(0, 0, 5, 5))
    c.shapes(ly.layer(2, 0)).insert(db.DBox(5, 5, 8, 8))
    c.shapes(ly.layer(63, 0)).insert(db.DText("edit", db.DTrans(db.DVector(6.5, 6.5))))
    res["gs_edit"] = ly
    return res


def main() -> None:
    OUT.mkdir(parents=True, exist_ok=True)
    with tempfile.TemporaryDirectory() as td:
        scripts = sorted(EXAMPLES.glob("*.py")) + [p for p in EXTRA if p.exists()]
        for py in scripts:
            ly = load_build(py)()
            gds = str(Path(td) / f"{py.stem}.gds")
            ly.write(gds)
            render(gds, str(OUT / f"{py.stem}.png"))
            print(f"rendered {py.stem}.png")
        for name, ly in gs_layouts().items():
            gds = str(Path(td) / f"{name}.gds")
            ly.write(gds)
            render(gds, str(OUT / f"{name}.png"))
            print(f"rendered {name}.png")


if __name__ == "__main__":
    main()
