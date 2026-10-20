"""Render clear applet surfaces and readable contextual menu backgrounds."""
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
                alpha = float(style.get("opacity", node.get("opacity", "1")))
                assert alpha == pytest.approx(.55)
        # The preset owns the colored gradient. The capsule may retain only
        # a faint edge reflection; a baked dark cap would also affect Tahoe.
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
    for name, bounds in (("dialogs/background", (.54, .56)),
                         ("dialogs/launcher-search", (.54, .56)),
                         ("widgets/panel-background", (.005, .025)),
                         ("widgets/tooltip", (.54, .56)),
                         ("widgets/background", (.54, .56)),
                         ("widgets/translucentbackground", (.54, .56))):
        renderer = svg.QSvgRenderer(gzip.decompress((ROOT / f"MacTahoeLiquidKde-{mode}/{name}.svgz").read_bytes()))
        image = gui.QImage(64, 64, gui.QImage.Format.Format_ARGB32)
        image.fill(0)
        painter = gui.QPainter(image)
        renderer.render(painter, "center", core.QRectF(0, 0, 64, 64))
        painter.end()
        alpha = image.pixelColor(32, 32).alphaF()
        assert bounds[0] <= alpha <= bounds[1], (mode, name, alpha)
        if name.startswith("dialogs/"):
            # Render at 200% so the subpixel contour covers a complete pixel.
            size = renderer.boundsOnElement("top").size().toSize() * 2
            edge = gui.QImage(size, gui.QImage.Format.Format_ARGB32)
            edge.fill(0)
            painter = gui.QPainter(edge)
            renderer.render(painter, "top", core.QRectF(0, 0, size.width(), size.height()))
            painter.end()
            rim = edge.pixelColor(size.width() // 2, 0).alphaF()
            interior = edge.pixelColor(size.width() // 2, size.height() // 2).alphaF()
            assert .54 <= interior <= .56 and interior < rim < .75, (mode, name, rim, interior)
            fill = image.pixelColor(32, 32)
            expected = 255 if mode == "Light" else 0
            assert abs(fill.red() - expected) <= 1
            assert fill.red() == fill.green() == fill.blue()



@pytest.mark.parametrize("mode", ["", "Dark"])
def test_kvantum_blur_corners_match_drawn_svg(mode):
    import configparser
    svg = pytest.importorskip("PyQt6.QtSvg")
    folder = ROOT.parent / "kvantum/mac-tahoe-liquid-kde"
    theme = "mac-tahoe-liquid-kde" + mode
    config = configparser.ConfigParser(strict=False, interpolation=None)
    config.read(folder / (theme + ".kvconfig"))
    renderer = svg.QSvgRenderer(str(folder / (theme + ".svg")))
    for surface in ("menu", "tooltip"):
        corner = renderer.boundsOnElement(surface + "-normal-topleft")
        radius = float(config["%General"][surface + "_blur_radius"])
        assert abs(corner.width() - radius) < .01
        assert abs(corner.height() - radius) < .01


def test_dock_assets_are_identical_between_modes():
    assert (ROOT / "MacTahoeLiquidKde-Light/widgets/panel-background.svgz").read_bytes() == (
        ROOT / "MacTahoeLiquidKde-Dark/widgets/panel-background.svgz").read_bytes()


@pytest.mark.parametrize("mode", ["Light", "Dark"])
@pytest.mark.parametrize("name", ["dialogs/background", "dialogs/launcher-search",
                                  "widgets/tooltip", "widgets/panel-background"])
def test_surface_contours_have_same_dark_outer_and_light_inner_line(mode, name):
    svg = pytest.importorskip("PyQt6.QtSvg")
    gui = pytest.importorskip("PyQt6.QtGui")
    core = pytest.importorskip("PyQt6.QtCore")
    renderer = svg.QSvgRenderer(gzip.decompress((ROOT / f"MacTahoeLiquidKde-{mode}/{name}.svgz").read_bytes()))
    size = renderer.boundsOnElement("top").size().toSize() * 4
    image = gui.QImage(size, gui.QImage.Format.Format_ARGB32)
    image.fill(0)
    painter = gui.QPainter(image)
    renderer.render(painter, "top", core.QRectF(0, 0, size.width(), size.height()))
    painter.end()
    x = size.width() // 2
    outer, inner, body = (image.pixelColor(x, y) for y in (1, 4, 12))
    assert outer.red() < inner.red(), (mode, name, outer.getRgb(), inner.getRgb())
    assert outer.alphaF() > body.alphaF() and inner.alphaF() > body.alphaF()
    # Two adjacent .75 logical-pixel contours; no wider third border.
    assert image.pixelColor(x, 7) == body


@pytest.mark.parametrize("mode", ["Light", "Dark"])
def test_all_dock_corners_keep_both_contours(mode):
    svg = pytest.importorskip("PyQt6.QtSvg")
    gui = pytest.importorskip("PyQt6.QtGui")
    core = pytest.importorskip("PyQt6.QtCore")
    renderer = svg.QSvgRenderer(gzip.decompress((ROOT / f"MacTahoeLiquidKde-{mode}/widgets/panel-background.svgz").read_bytes()))
    for prefix in ("", "south-"):
        for corner in ("topleft", "topright", "bottomleft", "bottomright"):
            image = gui.QImage(128, 128, gui.QImage.Format.Format_ARGB32)
            image.fill(0)
            painter = gui.QPainter(image)
            renderer.render(painter, prefix + corner, core.QRectF(0, 0, 128, 128))
            painter.end()
            contour = [image.pixelColor(x, y) for x in range(128) for y in range(128)
                       if image.pixelColor(x, y).alphaF() > .15]
            assert any(c.red() < 40 for c in contour), (prefix, corner, "dark line missing")
            assert any(c.red() > 240 for c in contour), (prefix, corner, "light line missing")
