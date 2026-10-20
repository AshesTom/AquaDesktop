"""Native regressions for desktop eligibility and per-frame corner handoff."""
import os
from pathlib import Path
import shlex
import shutil
import subprocess
import tarfile

import pytest

from rounded_corners_compat import apply
from steps import rounded_corners


@pytest.fixture(scope="module")
def qt_compile(tmp_path_factory):
    if not shutil.which("c++") or not shutil.which("pkg-config"):
        pytest.skip("C++ and Qt6Core development files required")
    flags = subprocess.run(["pkg-config", "--cflags", "--libs", "Qt6Core"],
                           capture_output=True, text=True, timeout=10)
    if flags.returncode:
        pytest.skip("Qt6Core development files required")
    work = tmp_path_factory.mktemp("corner-native")

    def compile_run(source):
        cpp = work / "probe.cpp"
        binary = work / "probe"
        cpp.write_text(source)
        subprocess.run(["c++", "-std=c++20", "-fPIC", str(cpp), "-o", str(binary),
                        *shlex.split(flags.stdout)], check=True, capture_output=True, timeout=60)
        subprocess.run([str(binary)], check=True, capture_output=True, timeout=10)
    return compile_run


def test_glass_uses_runtime_shape_without_mutating_preferences(qt_compile):
    source = (Path(__file__).resolve().parents[1] /
              "src/offline/kwin-effects/acrylic-glass/src/effect.cpp").read_text()
    handoff = source.split("    float cornerSquircle = 0.0f;", 1)[1].split(
        "    // Clamp the radius", 1)[0]
    qt_compile(r'''
#include <QObject>
#include <QVariant>
#include <QRectF>
#include <algorithm>
#include <cassert>
struct BorderRadius {
    float radius = 22;
    BorderRadius() = default;
    BorderRadius(float a, float, float, float) : radius(a) {}
};
struct Window : QObject {
    QRectF frameGeometry() const { return QRectF(0, 0, 640, 480); }
};
void check(Window *w, float expectedRadius, float expectedSquircle) {
    float topCornerRadius = 22, bottomCornerRadius = 22, cornerSquircle = 0;
    BorderRadius cornerRadius;
    QRectF surfaceRect(12, 8, 600, 450);
''' + handoff + r'''
    assert(topCornerRadius == expectedRadius && bottomCornerRadius == expectedRadius);
    assert(cornerRadius.radius == expectedRadius && cornerSquircle == expectedSquircle);
    if (w->property("_mttkde_corner_shape_v1").toList().size() == 2)
        assert(surfaceRect == w->frameGeometry());
}
int main() {
    Window window;
    check(&window, 22, 0);
    window.setProperty("_mttkde_corner_shape_v1", QVariantList{28.0, 0.5});
    check(&window, 28, 0.5);
    window.setProperty("_mttkde_corner_shape_v1", QVariantList{13.5, 1.0});
    check(&window, 13.5, 1);
    window.setProperty("_mttkde_corner_shape_v1", QVariantList{0.0, 0.0});
    check(&window, 0, 0);
    window.setProperty("_mttkde_corner_shape_v1", QVariant());
    check(&window, 22, 0);
    window.setProperty("_mttkde_corner_shape_v1", QVariantList{28.0});
    check(&window, 22, 0);
}
''')


@pytest.mark.skipif(not os.environ.get("MTTKDE_ROUNDED_CORNERS_ARCHIVE"),
                    reason="requires the pinned source archive")
def test_desktop_never_redirects_even_when_explicitly_included(tmp_path, qt_compile):
    archive = Path(os.environ["MTTKDE_ROUNDED_CORNERS_ARCHIVE"])
    assert rounded_corners._archive_is_valid(archive)
    with tarfile.open(archive) as tar:
        tar.extractall(tmp_path, filter="data")
    source = tmp_path / f"KDE-Rounded-Corners-{rounded_corners.UPSTREAM_VERSION}"
    apply(source)
    window = (source / "src/Window.cpp").read_text()
    gate = window.split("bool ShapeCorners::Window::hasEffect() const\n{", 1)[1].split("\n}", 1)[0]
    effect = (source / "src/Effect.cpp").read_text()
    added = effect.split("void ShapeCorners::Effect::windowAdded(KWin::EffectWindow *kwindow)\n{", 1)[1].split("\n}", 1)[0]
    qt_compile(r'''
#include <cassert>
struct Geometry { bool isValid() const { return true; } };
namespace KWin {
struct EffectWindow {
    bool desktop = false, dock = false, normal = true, dialog = false;
    bool isDesktop() const { return desktop; }
    bool isDock() const { return dock; }
    bool isNormalWindow() const { return normal; }
    bool isDialog() const { return dialog; }
    Geometry expandedGeometry() const { return {}; }
};
}
struct Config {
    static bool includeNormalWindows() { return true; }
    static bool includeDialogs() { return true; }
};
struct Window {
    KWin::EffectWindow *w;
    bool isIncluded = false, isExcluded = false;
    bool hasRoundCorners() const { return true; }
    bool hasOutline() const { return true; }
    bool hasEffect() const {
''' + gate + r'''
    }
};
struct Manager {
    int added = 0;
    bool addWindow(KWin::EffectWindow *) { ++added; return true; }
};
struct Effect {
    Manager *m_windowManager;
    void redirect(KWin::EffectWindow *) { assert(false); }
    void windowAdded(KWin::EffectWindow *kwindow) {
''' + added + r'''
    }
};
int main() {
    KWin::EffectWindow native;
    Window window{&native};
    assert(window.hasEffect());
    native.desktop = true;
    assert(!window.hasEffect());
    window.isIncluded = true;
    assert(!window.hasEffect());
    native.desktop = false;
    native.dock = true;
    assert(!window.hasEffect());
    native.dock = false;
    native.normal = false;
    native.dialog = true;
    assert(window.hasEffect());
    window.isExcluded = true;
    assert(!window.hasEffect());
    Manager manager;
    Effect effect{&manager};
    effect.windowAdded(&native);
    assert(manager.added == 1);
}
''')
