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


def main() -> None:
    OUT.mkdir(parents=True, exist_ok=True)
    with tempfile.TemporaryDirectory() as td:
        for py in sorted(EXAMPLES.glob("*.py")):
            ly = load_build(py)()
            gds = str(Path(td) / f"{py.stem}.gds")
            ly.write(gds)
            png = str(OUT / f"{py.stem}.png")
            render(gds, png)
            print(f"rendered {png}")


if __name__ == "__main__":
    main()
