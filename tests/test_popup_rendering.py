"""Real parsers/renderers for popup surfaces and Xwayland blur requests."""

import os
import subprocess
import sys

import pytest


def test_light_and_dark_menu_surfaces_have_equal_effective_opacity(repo):
    svg = pytest.importorskip("PyQt6.QtSvg")
    gui = pytest.importorskip("PyQt6.QtGui")
    core = pytest.importorskip("PyQt6.QtCore")
    import configparser

    samples = []
    for name in ("mac-tahoe-liquid-kde", "mac-tahoe-liquid-kdeDark"):
        root = repo / "src/offline/kvantum/mac-tahoe-liquid-kde"
        config = configparser.ConfigParser(interpolation=None, strict=False)
        config.read(root / (name + ".kvconfig"))
        factor = 1 - int(config["%General"]["reduce_menu_opacity"]) / 100
        renderer = svg.QSvgRenderer((root / (name + ".svg")).read_bytes())
        alphas = []
        for element in ("menu-normal", "path4382-5", "path4714-2"):
            image = gui.QImage(64, 64, gui.QImage.Format.Format_ARGB32)
            image.fill(0)
            painter = gui.QPainter(image)
            renderer.render(painter, element, core.QRectF(0, 0, 64, 64))
            painter.end()
            alphas.append(image.pixelColor(48, 48).alpha() * factor)
        assert len(set(alphas)) == 1, "Popup frame and interior must match"
        samples.append(alphas[0])
    assert samples[0] == samples[1] and 130 <= samples[0] <= 150


def test_gtk4_stylesheets_parse_without_errors(repo, tmp_path):
    gi = pytest.importorskip("gi")
    if not callable(getattr(gi, "require_version", None)):
        pytest.skip("PyGObject required; the gi namespace alone is insufficient")
    script = """
import gi, pathlib, sys
try: gi.require_version('Gtk','4.0')
except ValueError: sys.exit(77)
from gi.repository import Gtk
errors=[]
for path in pathlib.Path(sys.argv[1]).glob('*/gtk-4.0/*.css'):
    provider=Gtk.CssProvider()
    provider.connect('parsing-error',lambda p,s,e: errors.append(str(e)) if e.domain=='gtk-css-parser-error-quark' else None)
    provider.load_from_path(str(path))
assert not errors, errors
"""
    env = os.environ | {
        "GTK_THEME": "Adwaita",
        "XDG_CONFIG_HOME": str(tmp_path),
        "HOME": str(tmp_path),
    }
    result = subprocess.run(
        [sys.executable, "-c", script, str(repo / "src/offline/gtk")],
        env=env,
        capture_output=True,
        text=True,
        timeout=30,
    )
    if result.returncode == 77:
        pytest.skip("GTK4 introspection required")
    assert result.returncode == 0, result.stdout + result.stderr
