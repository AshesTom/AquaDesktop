"""Real parsers/renderers for popup surfaces and Xwayland blur requests."""

import os
import shlex
import shutil
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
    # Context menus retain a translucent but substantial fill in both modes.
    assert samples[0] == samples[1] and 195 <= samples[0] <= 210


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


def test_xwayland_property_is_read_and_invalid_data_never_means_full_blur(
    repo, tmp_path
):
    for tool in ("Xvfb", "c++", "pkg-config"):
        if not shutil.which(tool):
            pytest.skip(f"{tool} required")
    flags = subprocess.run(
        ["pkg-config", "--cflags", "--libs", "Qt6Gui", "xcb"],
        capture_output=True,
        text=True,
        timeout=10,
    )
    if flags.returncode:
        pytest.skip("Qt6Gui and XCB development files required")
    source = (
        repo / "src/offline/kwin-effects/acrylic-glass/src/effect.cpp"
    ).read_text()
    block = source.split("    // Xwayland still advertises blur", 1)[1].split(
        "    // Wayland: prefer", 1
    )[0]
    block = block[block.index("#if KWIN_BUILD_X11") :]
    code = (
        r"""
#include <QRegion>
#include <QRect>
#include <xcb/xcb.h>
#include <memory>
#include <optional>
#include <climits>
#include <cstdlib>
#include <cassert>
#include <vector>
#define KWIN_BUILD_X11 1
using Region=QRegion;
using Rect=QRect;
namespace Xcb { struct Result { QRect rect; QRect toRect() const { return rect; } }; Result fromXNative(QRect r) { return {r}; } }
struct Window { xcb_window_t id; long windowId() const { return id; } };
struct Effects { xcb_connection_t *connection; xcb_connection_t *xcbConnection() const { return connection; } };
std::optional<Region> read(Effects *effects, Window *w, xcb_atom_t net_wm_blur_region) {
    std::optional<Region> content;
"""
        + block
        + r"""
    return content;
}
int main() {
    auto *connection=xcb_connect(nullptr,nullptr);assert(!xcb_connection_has_error(connection));
    auto *screen=xcb_setup_roots_iterator(xcb_get_setup(connection)).data;
    auto id=xcb_generate_id(connection);
    xcb_create_window(connection,XCB_COPY_FROM_PARENT,id,screen->root,0,0,100,100,0,XCB_WINDOW_CLASS_INPUT_OUTPUT,screen->root_visual,0,nullptr);
    const char name[]="_KDE_NET_WM_BLUR_BEHIND_REGION";
    auto *reply=xcb_intern_atom_reply(connection,xcb_intern_atom(connection,false,sizeof(name)-1,name),nullptr);
    auto atom=reply->atom;free(reply);
    Effects effects{connection};Window w{id};
    assert(!read(&effects,&w,atom));
    auto set=[&](std::vector<uint32_t> data,xcb_atom_t type=XCB_ATOM_CARDINAL) {
        xcb_change_property(connection,XCB_PROP_MODE_REPLACE,id,atom,type,32,data.size(),data.data());xcb_flush(connection);
    };
    set({});assert(read(&effects,&w,atom).has_value() && read(&effects,&w,atom)->isEmpty());
    set({3,4,20,30});assert(*read(&effects,&w,atom)==QRegion(QRect(3,4,20,30)));
    set({3,4,20});assert(!read(&effects,&w,atom));
    set({3,4,20,30},XCB_ATOM_STRING);assert(!read(&effects,&w,atom));
    set({3,4,UINT32_MAX,30});assert(!read(&effects,&w,atom));
    set({uint32_t(INT_MAX),4,20,30});assert(!read(&effects,&w,atom));
    set(std::vector<uint32_t>(16388,1));assert(!read(&effects,&w,atom));
    w.id=0;assert(!read(&effects,&w,atom));
    xcb_disconnect(connection);
}
"""
    )
    cpp = tmp_path / "property.cpp"
    cpp.write_text(code)
    binary = tmp_path / "property"
    result = subprocess.run(
        [
            "c++",
            "-std=c++20",
            "-fPIC",
            str(cpp),
            "-o",
            str(binary),
            *shlex.split(flags.stdout),
        ],
        capture_output=True,
        text=True,
        timeout=60,
    )
    assert result.returncode == 0, result.stderr
    read_fd, write_fd = os.pipe()
    server = subprocess.Popen(
        [
            "Xvfb",
            "-displayfd",
            str(write_fd),
            "-screen",
            "0",
            "640x480x24",
            "-nolisten",
            "tcp",
        ],
        pass_fds=(write_fd,),
        stdout=subprocess.DEVNULL,
        stderr=subprocess.DEVNULL,
    )
    os.close(write_fd)
    try:
        import select

        assert select.select([read_fd], [], [], 10)[0], "Xvfb did not start"
        display = os.read(read_fd, 32).decode().strip()
        subprocess.run(
            [str(binary)],
            env=os.environ | {"DISPLAY": ":" + display},
            check=True,
            timeout=10,
        )
    finally:
        os.close(read_fd)
        server.terminate()
        server.wait(timeout=10)
