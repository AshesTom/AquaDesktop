"""Volume HUD of the menu bar's Sound extra (AquaDesktop).

macOS Tahoe answers the volume keys with the sound bubble right under the
Sound menu extra (measured on a Tahoe capture), not with a big overlay in
the middle of the screen. The Sound extra hears the keys from KGlobalAccel
on the session bus and shows its own HUD; the layout step turns
plasma-pa's on-screen display for volume and mute off.
"""

import os
import shutil
import subprocess
import sys
import textwrap
from pathlib import Path

import pytest

REPO = Path(__file__).resolve().parent.parent
UI = REPO / "src/offline/plasmoids/org.kde.mac-tahoe-liquid-kde.volume/contents/ui"
sys.path.insert(0, str(REPO / "src/scripts"))

from steps import layout  # noqa: E402


def test_hud_listens_to_the_volume_keys_through_kglobalaccel():
    keys = (UI / "VolumeKeys.qml").read_text()
    assert 'service: "org.kde.kglobalaccel"' in keys
    assert 'path: "/component/kmix"' in keys
    assert 'iface: "org.kde.kglobalaccel.Component"' in keys
    # SignalWatcher calls "dbus" + the signal name, with wrapped values.
    assert "function dbusglobalShortcutPressed(component, action, timestamp)" in keys
    assert "keys.actions.includes(String(action))" in keys
    for action in ("increase_volume", "decrease_volume", "increase_volume_small",
                   "decrease_volume_small", "mute"):
        assert f'"{action}"' in keys
    main = (UI / "main.qml").read_text()
    # A missing D-Bus QML module only loses the HUD.
    assert 'source: "VolumeKeys.qml"' in main
    assert "import org.kde.plasma.workspace.dbus" not in main
    assert "onLoaded: item.pressed.connect(root.showHud)" in main


def test_hud_is_an_on_screen_display_under_the_extra():
    main = (UI / "main.qml").read_text()
    hud = main[main.index("id: hudWindow"):]
    assert "type: PlasmaCore.Dialog.OnScreenDisplay" in hud
    assert "Qt.WindowDoesNotAcceptFocus" in hud
    assert "outputOnly: true" in hud
    assert "hud: true" in hud and "interactive: false" in hud
    assert "readonly property int hudTimeout: 1500" in main
    # 11 px under the menu bar on the capture, the menu 2 px.
    assert "readonly property int hudDrop: 9" in main
    assert "hudWindow.y += root.hudDrop;" in main
    # The extra stays highlighted while the HUD shows; never over the menu.
    assert "visible: popover.visible || hudWindow.visible" in main
    assert "if (popover.visible || !root.sink) {" in main


def test_hud_metrics_follow_the_tahoe_capture():
    view = (UI / "VolumeView.qml").read_text()
    assert "implicitWidth: hud ? 292 : 322" in view
    assert "implicitHeight: hud ? 64 : 68" in view
    for line in ("titleY: hud ? 18 : 19", "sliderY: hud ? 41 : 45",
                 "trackLeft: hud ? 31 : 38", "trackRight: hud ? 39 : 42",
                 "trackHeight: hud ? 4 : 6"):
        assert f"readonly property int {line}" in view
    # 17 tick dots, 3 px under the HUD's track.
    assert "model: 17" in view
    assert "y: view.hud ? track.height + 3" in view
    bubble = (UI / "SoundBubble.qml").read_text()
    assert "property alias hud: view.hud" in bubble
    assert "readonly property real glassRadius: radius" in bubble


class _Config(dict):
    def write(self, *args):
        file, group, key, value = args[1], args[3], args[5], args[6]
        if value == "--delete":
            self.pop((file, group, key), None)
        else:
            self[(file, group, key)] = value
        return True

    def read(self, file, group, key):
        return self.get((file, group, key), "")


def test_layout_turns_plasmas_volume_osd_off(monkeypatch):
    config = _Config()
    monkeypatch.setattr(layout, "kw_write", config.write)
    monkeypatch.setattr(layout, "kw_read", config.read)
    messages = []
    monkeypatch.setattr(layout, "ok", messages.append)

    layout._use_sound_hud()

    assert config == {("plasmaparc", "General", "VolumeOsd"): "false",
                      ("plasmaparc", "General", "MuteOsd"): "false"}
    assert messages == ["Volume keys show the macOS volume HUD"]


def test_uninstall_gives_the_osd_back_unless_the_user_changed_it(monkeypatch):
    config = _Config({("plasmaparc", "General", "VolumeOsd"): "false",
                      ("plasmaparc", "General", "MuteOsd"): "true"})
    monkeypatch.setattr(layout, "kw_write", config.write)
    monkeypatch.setattr(layout, "kw_read", config.read)

    layout._restore_volume_osd()

    assert config == {("plasmaparc", "General", "MuteOsd"): "true"}


def test_install_and_uninstall_call_the_osd_switch():
    source = (REPO / "src/scripts/steps/layout.py").read_text()
    install = source[source.index("def install()"):source.index("def _use_sound_hud()")]
    assert "_use_sound_hud()" in install
    uninstall = source[source.index("def uninstall()"):]
    assert "_restore_volume_osd()" in uninstall


_EMITTER = textwrap.dedent('''
    import sys
    from PyQt6.QtCore import QCoreApplication, QTimer
    from PyQt6.QtDBus import QDBusConnection, QDBusMessage
    app = QCoreApplication(sys.argv)
    bus = QDBusConnection.sessionBus()
    assert bus.registerService("org.kde.kglobalaccel")
    def emit(action):
        msg = QDBusMessage.createSignal("/component/kmix", "org.kde.kglobalaccel.Component",
                                        "globalShortcutPressed")
        msg.setArguments(["kmix", action, 1])
        bus.send(msg)
    QTimer.singleShot(1500, lambda: emit("show_desktop"))
    QTimer.singleShot(1700, lambda: emit("increase_volume"))
    QTimer.singleShot(1900, lambda: emit("mute"))
    QTimer.singleShot(2600, app.quit)
    app.exec()
''')

_LISTENER = textwrap.dedent('''
    import sys
    from PyQt6.QtCore import QTimer, QUrl
    from PyQt6.QtGui import QGuiApplication
    from PyQt6.QtQml import QQmlComponent, QQmlEngine
    app = QGuiApplication(sys.argv)
    engine = QQmlEngine()
    component = QQmlComponent(engine, QUrl.fromLocalFile(sys.argv[1]))
    keys = component.create()
    if keys is None:
        print("ERROR", component.errorString())
        sys.exit(3)
    keys.pressed.connect(lambda: print("PRESSED", flush=True))
    QTimer.singleShot(3000, app.quit)
    app.exec()
''')


def test_volume_keys_heard_on_a_private_bus(tmp_path):
    pytest.importorskip("PyQt6.QtDBus")
    pytest.importorskip("PyQt6.QtQml")
    if not shutil.which("dbus-run-session"):
        pytest.skip("dbus-run-session not available")
    (tmp_path / "emit.py").write_text(_EMITTER)
    (tmp_path / "listen.py").write_text(_LISTENER)
    script = tmp_path / "run.sh"
    script.write_text(
        f'"{sys.executable}" -I "{tmp_path}/emit.py" &\n'
        "sleep 0.5\n"
        f'"{sys.executable}" -I "{tmp_path}/listen.py" "{UI}/VolumeKeys.qml"\n'
        "wait\n")
    env = {key: value for key, value in os.environ.items()
           if key not in ("DBUS_SESSION_BUS_ADDRESS",)}
    env.update({"QT_QPA_PLATFORM": "offscreen", "XDG_CONFIG_HOME": str(tmp_path / "config"),
                "XDG_CACHE_HOME": str(tmp_path / "cache")})
    result = subprocess.run(["dbus-run-session", "--", "bash", str(script)], env=env,
                            capture_output=True, text=True, timeout=60)
    out = result.stdout + result.stderr
    if 'module "org.kde.plasma.workspace.dbus" is not installed' in out:
        pytest.skip("Plasma's D-Bus QML module is not installed")
    assert "ERROR" not in result.stdout, out
    # Two volume keys; the unrelated shortcut is ignored.
    assert result.stdout.count("PRESSED") == 2, out
