"""Shared glass surfaces preserve masks, shadows and high transparency."""
import gzip
from pathlib import Path
import xml.etree.ElementTree as ET

import pytest

ROOT = Path(__file__).resolve().parents[1] / "src/offline/plasma-theme"


def _xml(path):
    return ET.fromstring(gzip.decompress(path.read_bytes()))


@pytest.mark.parametrize("mode", ["Light", "Dark"])
def test_shared_dialog_fills_keep_top_bar_clear(mode):
    source = ROOT / f"MacTahoeLiquidKde-{mode}"
    for file in ("dialogs/background.svgz", "dialogs/launcher-search.svgz"):
        root = _xml(source / file)
        center = next(n for n in root.iter() if n.get("id") == "center")
        for node in center.iter():
            if node.tag.endswith("}rect"):
                style = dict(part.split(":", 1) for part in node.get("style", "").split(";") if ":" in part)
                assert 0 < float(style.get("opacity", node.get("opacity", "1"))) <= 0.2
        # The preset owns the colored gradient. The capsule may retain only
        # a faint edge reflection; a baked dark cap would also affect Clear.
        for node in root.iter():
            if node.get("id") in ("top-surface", "bottom-surface"):
                assert all(float(stop.get("stop-opacity", "1")) <= 0.08 for stop in node)
    panel = _xml(source / "widgets/panel-background.svgz")
    top = next(n for n in panel.iter() if n.get("id") == "north-center")
    assert "fill:none" in top.get("style", "")



@pytest.mark.parametrize("mode", ["Light", "Dark"])
def test_qt_renders_transparent_dialogs_and_dock(mode):
    svg = pytest.importorskip("PyQt6.QtSvg")
    gui = pytest.importorskip("PyQt6.QtGui")
    core = pytest.importorskip("PyQt6.QtCore")
    for name in ("dialogs/background", "dialogs/launcher-search", "widgets/panel-background"):
        renderer = svg.QSvgRenderer(gzip.decompress((ROOT / f"MacTahoeLiquidKde-{mode}/{name}.svgz").read_bytes()))
        image = gui.QImage(64, 64, gui.QImage.Format.Format_ARGB32)
        image.fill(0)
        painter = gui.QPainter(image)
        renderer.render(painter, "center", core.QRectF(0, 0, 64, 64))
        painter.end()
        assert 0 < image.pixelColor(32, 32).alphaF() <= .21, (mode, name)
