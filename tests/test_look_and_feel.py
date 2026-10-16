"""Global theme screens drawn like macOS (AquaDesktop).

The look-and-feel packages replace Breeze's session splash ("Plasma made
by KDE") with the Mac's start-up screen and Breeze's full-screen logout
page with a macOS Tahoe alert. Both variants ship the same files.
"""

import json
import os
import re
import subprocess
import sys
import textwrap
from pathlib import Path

import pytest

REPO = Path(__file__).resolve().parent.parent
LAF = REPO / "src/offline/look-and-feel"
VARIANTS = [LAF / "MacTahoeLiquidKde-Dark", LAF / "MacTahoeLiquidKde-Light"]
DARK = VARIANTS[0] / "contents"
PLYMOUTH = REPO / "src/offline/plymouth/MacTahoeLiquidKde"
LOGOUT_QML = DARK / "logout/Logout.qml"
SPLASH_QML = DARK / "splash/Splash.qml"


def _tree(root: Path) -> dict[str, bytes]:
    return {str(p.relative_to(root)): p.read_bytes() for p in sorted(root.rglob("*")) if p.is_file()}


@pytest.mark.parametrize("part", ["logout", "splash"])
def test_both_variants_ship_the_same_screens(part):
    dark, light = (_tree(v / "contents" / part) for v in VARIANTS)
    assert dark, f"{part} missing from the look-and-feel package"
    assert dark == light


def test_the_alert_reads_the_accent_like_the_menu_bar_popovers():
    shared = REPO / "src/offline/plasmoids/org.kde.mac-tahoe-liquid-kde.controlcenter/contents/ui/AccentColor.qml"
    assert (DARK / "logout/AccentColor.qml").read_bytes() == shared.read_bytes()


def test_window_switcher_survives_the_light_dark_switch():
    # plasma-apply-lookandfeel reverts kwinrc [TabBox] LayoutName to the
    # package's value on every switch: Breeze's here undid the Mac switcher.
    sys.path.insert(0, str(REPO / "src/scripts"))
    from steps import window_decorations

    for variant in VARIANTS:
        defaults = (variant / "contents/defaults").read_text()
        match = re.search(r"^\[kwinrc\]\[WindowSwitcher\]\nLayoutName=(.+)$", defaults, re.M)
        assert match, variant.name
        assert match.group(1) == window_decorations.SWITCHER


def test_splash_matches_the_plymouth_boot_screen():
    splash = SPLASH_QML.read_text()
    script = (PLYMOUTH / "MacTahoeLiquidKde.script").read_text()
    # Same logo, same proportions: boot and session start line up.
    assert (DARK / "splash/images/apple.svg").read_bytes() == (PLYMOUTH / "boot.svg").read_bytes()
    for ratio in ("0.07", "0.072", "0.035"):
        assert ratio in script
        assert ratio in splash
    assert 'color: "black"' in splash
    assert "Qt.rgba(1, 1, 1, 0.2)" in splash
    assert 'fill-opacity="0.2"' in (PLYMOUTH / "progress_track.svg").read_text()
    # Nothing of KDE's own splash is left.
    assert "plasma.svgz" not in splash and "kde.svgz" not in splash


def test_alert_keeps_the_greeter_contract():
    qml = LOGOUT_QML.read_text()
    for signal in ("logoutRequested()", "haltRequested()", "haltUpdateRequested()",
                   "suspendRequested(int spdMethod)", "rebootRequested()",
                   "rebootRequested2(int opt)", "rebootUpdateRequested()",
                   "cancelRequested()", "lockScreenRequested()",
                   "cancelSoftwareUpdateRequested()"):
        assert f"signal {signal}" in qml
    assert "width: screenGeometry.width" in qml
    assert "ShutdownType.ShutdownTypeDefault" in qml


def test_alert_looks_like_a_macos_alert():
    qml = LOGOUT_QML.read_text()
    assert "property int remainingTime: 60" in qml
    assert 'sequence: "Escape"' in qml
    assert "Are you sure you want to shut down your computer now?" in qml
    assert "radius: 26" in qml and "width: 300" in qml
    # No shader effect: on a GPU-less session it draws nothing, and an
    # invisible alert would still shut the computer down after 60 s.
    assert "QtQuick.Effects" not in qml and "MultiEffect" not in qml
    # The blur is optional: the compiled module is loaded through a Loader.
    assert 'source: "WindowBlur.qml"' in qml
    assert "import org.kde.mac.tahoe.liquid.glass" not in qml
    # No full-screen black page.
    assert "opacity: 0.85" not in qml


_HARNESS = textwrap.dedent('''
    import sys
    from PyQt6.QtCore import QObject, QRect, QUrl, pyqtSlot
    from PyQt6.QtGui import QGuiApplication
    from PyQt6.QtQuick import QQuickView

    qml, sdtype = sys.argv[1], int(sys.argv[2])
    updates = sys.argv[3] == "1"
    app = QGuiApplication(sys.argv)

    class I18n(QObject):
        @staticmethod
        def _fmt(text, *args):
            for i, arg in enumerate(args, 1):
                text = text.replace(f"%{i}", str(arg))
            return text

        @pyqtSlot(str, str, result=str)
        def i18nd(self, domain, text):
            return text

        @pyqtSlot(str, str, str, str, result=str)
        def i18ndc(self, domain, context, text, arg):
            return self._fmt(text, arg)

        @pyqtSlot(str, str, str, int, result=str)
        def i18ndp(self, domain, singular, plural, n):
            return self._fmt(singular if n == 1 else plural, n)

    view = QQuickView()
    i18n = I18n()
    ctx = view.rootContext()
    ctx.setContextObject(i18n)
    ctx.setContextProperty("screenGeometry", QRect(0, 0, 960, 600))
    ctx.setContextProperty("sdtype", sdtype)
    ctx.setContextProperty("ShutdownType", {
        "ShutdownTypeDefault": -1, "ShutdownTypeNone": 0, "ShutdownTypeReboot": 1,
        "ShutdownTypeHalt": 2, "ShutdownTypeLogout": 3})
    ctx.setContextProperty("maysd", True)
    ctx.setContextProperty("canLogout", True)
    ctx.setContextProperty("spdMethods", {"SuspendState": True, "HibernateState": False})
    ctx.setContextProperty("softwareUpdatePending", updates)
    ctx.setContextProperty("rebootToFirmwareSetup", False)
    ctx.setContextProperty("rebootToBootLoaderMenu", False)
    ctx.setContextProperty("rebootToBootLoaderEntry", "")
    ctx.setContextProperty("isUefi", True)
    view.setSource(QUrl.fromLocalFile(qml))
    for error in view.errors():
        print("ERROR", error.toString())
    root = view.rootObject()
    if root is None:
        sys.exit(3)

    def buttons(item):
        for child in item.childItems():
            if child.property("isDefault") is not None and child.isVisible():
                yield child
            yield from buttons(child)

    view.show()
    app.processEvents()
    fired = []
    for name in ("logoutRequested", "haltRequested", "haltUpdateRequested",
                 "rebootRequested", "rebootUpdateRequested", "cancelRequested"):
        getattr(root, name).connect(lambda name=name: fired.append(name))
    found = list(buttons(root))
    for button in found:
        print("BUTTON", "*" if button.property("isDefault") else "-", button.property("text"))
    for button in found:
        button.clicked.emit()
    print("FIRED", " ".join(fired))
''')


def _render(tmp_path, sdtype: int, updates: bool = False) -> list[str]:
    pytest.importorskip("PyQt6.QtQuick")
    harness = tmp_path / "harness.py"
    harness.write_text(_HARNESS)
    config = tmp_path / "config"
    config.mkdir(exist_ok=True)
    env = {
        **os.environ,
        "QT_QPA_PLATFORM": "offscreen",
        "XDG_CONFIG_HOME": str(config),
        "XDG_CACHE_HOME": str(tmp_path / "cache"),
        "XDG_DATA_HOME": str(tmp_path / "data"),
    }
    env.pop("DBUS_SESSION_BUS_ADDRESS", None)
    result = subprocess.run(
        [sys.executable, "-I", str(harness), str(LOGOUT_QML), str(sdtype), "1" if updates else "0"],
        env=env, capture_output=True, text=True, timeout=60,
    )
    out = result.stdout + result.stderr
    if 'module "org.kde.kirigami" is not installed' in out or \
            'module "org.kde.plasma.private.sessions" is not installed' in out:
        pytest.skip("Plasma's QML modules are not installed")
    errors = [line for line in result.stdout.splitlines() if line.startswith("ERROR")]
    assert result.returncode == 0 and not errors, out
    return result.stdout.splitlines()


@pytest.mark.parametrize("sdtype, buttons, fired", [
    (2, ["* Shut Down", "- Cancel"], "haltRequested cancelRequested"),
    (1, ["* Restart", "- Cancel"], "rebootRequested cancelRequested"),
    (0, ["* Log Out", "- Cancel"], "logoutRequested cancelRequested"),
    (-1, ["* Shut Down", "- Restart", "- Sleep", "- Log Out", "- Cancel"],
     "haltRequested rebootRequested logoutRequested cancelRequested"),
])
def test_alert_buttons_send_the_greeter_signals(tmp_path, sdtype, buttons, fired):
    lines = _render(tmp_path, sdtype)
    assert [line[len("BUTTON "):] for line in lines if line.startswith("BUTTON")] == buttons
    assert f"FIRED {fired}" in lines


def test_alert_offers_updates_first_when_they_are_pending(tmp_path):
    lines = _render(tmp_path, 2, updates=True)
    assert [line[len("BUTTON "):] for line in lines if line.startswith("BUTTON")] == [
        "* Update and Shut Down", "- Shut Down Without Updating", "- Cancel"]
    assert "FIRED haltUpdateRequested haltRequested cancelRequested" in lines


def test_metadata_still_points_at_breeze_for_the_rest():
    for variant in VARIANTS:
        meta = json.loads((variant / "metadata.json").read_text())
        assert meta["KPackageStructure"] == "Plasma/LookAndFeel"
        assert meta["X-KDE-fallbackPackage"].startswith("org.kde.breeze")
