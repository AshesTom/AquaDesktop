"""Real parsers/renderers for popup surfaces and Xwayland blur requests."""

import os
import subprocess
import sys

import pytest


# AquaDesktop keeps its own Kvantum menus (light 60 %, dark opaque face):
# upstream's equal light/dark menu opacity check does not apply.


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
