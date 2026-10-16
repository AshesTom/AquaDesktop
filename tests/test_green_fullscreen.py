"""Green traffic light → full screen KWin script (AquaDesktop).

On macOS the green title bar button enters full screen while a title
bar double-click only zooms. The KWin script recognises a maximize
requested while the cursor sits on the green button's slot of the
Aurorae layout, so the slot it hard-codes must match the decoration.
"""

import configparser
import json
import re
import shutil
from pathlib import Path

import pytest

REPO = Path(__file__).resolve().parent.parent
SCRIPT = REPO / "src/offline/kwin-scripts/mac-tahoe-green-fullscreen"
MAIN_QML = SCRIPT / "contents/ui/main.qml"
AURORAE = REPO / "src/offline/aurorae"


def _const(name: str) -> int:
    match = re.search(rf"readonly property int {name}: (\d+)", MAIN_QML.read_text())
    assert match, f"{name} missing from main.qml"
    return int(match.group(1))


def test_metadata_is_a_kwin_script_named_after_its_folder():
    meta = json.loads((SCRIPT / "metadata.json").read_text())
    assert meta["KPackageStructure"] == "KWin/Script"
    assert meta["X-Plasma-API"] == "declarativescript"
    assert (SCRIPT / "contents" / meta["X-Plasma-MainScript"]).is_file()
    assert meta["KPlugin"]["Id"] == SCRIPT.name
    assert "Pear" not in json.dumps(meta)


def test_script_decides_before_the_zoom_and_registers_the_shortcut():
    qml = MAIN_QML.read_text()
    # The frame is already maximized when maximizedChanged fires, so the
    # cursor test must run on maximizedAboutToChange.
    assert "maximizedAboutToChange.connect" in qml
    assert "maximizedChanged.connect" in qml
    assert "window.setMaximize(false, false)" in qml
    assert 'name: "MacTahoeToggleFullScreen"' in qml
    assert 'sequence: "Ctrl+Meta+F"' in qml
    # QML treats on<Upper> names as handlers: the per-window callbacks
    # must not use them (only Connections handlers may).
    assert "root.handleMaximizeRequest(window, mode)" in qml
    assert not re.search(r"function onMaximiz", qml)


def test_full_screen_keeps_the_menu_bar_reachable():
    """macOS full screen, not KWin's: the window covers the panels only
    while it is the active space, and the top edge brings the menu bar
    back over it without moving or resizing the window."""
    qml = MAIN_QML.read_text()
    assert "window.fullScreen = true" not in qml
    assert "window.keepAbove = true" in qml
    assert "KWin.Workspace.FullScreenArea" in qml
    assert "KWin.Workspace.MaximizeArea" in qml
    assert 'setReveal("top")' in qml and 'setReveal("bottom")' in qml
    assert "!menusOpen()" in qml
    # The client always keeps the full screen size.
    assert "area.width + b.left + b.right, area.height + b.top + b.bottom" in qml


@pytest.mark.parametrize("variant", ["Dark", "Light"])
def test_green_slot_matches_the_aurorae_layout(variant):
    rc = configparser.ConfigParser(strict=False)
    rc.optionxform = str
    rc.read(AURORAE / f"MacTahoeLiquidKde-{variant}rc")
    assert rc["General"]["LeftButtons"] == "XIA"
    layout = rc["Layout"]
    edge = int(layout["TitleEdgeLeft"])
    width = int(layout["ButtonWidth"])
    spacing = int(layout["ButtonSpacing"])

    yellow_end = edge + 2 * width + spacing
    green_start = edge + 2 * (width + spacing)
    green_end = green_start + width
    left, right = _const("greenLeft"), _const("greenRight")

    assert yellow_end < left <= green_start
    assert green_end <= right
    # Slack past the button stays under one button gap.
    assert right - green_end < spacing


def _patch_step(monkeypatch, tmp_path, writes):
    from steps import window_decorations as wd

    fake = tmp_path / "offline"
    for variant in ("Dark", "Light"):
        (fake / "aurorae" / f"MacTahoeLiquidKde-{variant}").mkdir(parents=True)
    script = fake / "kwin-scripts" / wd.FULLSCREEN_SCRIPT
    (script / "contents/ui").mkdir(parents=True)
    (script / "metadata.json").write_text("{}")
    (script / "contents/ui/main.qml").write_text("// test")

    monkeypatch.setattr(wd, "offline", lambda *parts: fake.joinpath(*parts))
    monkeypatch.setattr(wd, "DEST_DIR", tmp_path / "aurorae/themes")
    monkeypatch.setattr(wd, "SCRIPTS_DIR", tmp_path / "kwin/scripts")
    monkeypatch.setattr(wd, "kw_write", lambda *a: writes.append(a) or True)
    monkeypatch.setattr(wd, "qdbus_call", lambda *_a: True)
    monkeypatch.setattr(wd, "theme_mode", lambda: "dark")
    for name in ("ok", "warn", "info", "fail", "reinstall"):
        monkeypatch.setattr(wd, name, lambda _msg: None)
    return wd


def test_install_copies_and_enables_the_script(tmp_path, monkeypatch):
    writes: list[tuple] = []
    wd = _patch_step(monkeypatch, tmp_path, writes)
    wd.install()

    dest = tmp_path / "kwin/scripts" / wd.FULLSCREEN_SCRIPT
    assert (dest / "contents/ui/main.qml").is_file()
    assert any(f"{wd.FULLSCREEN_SCRIPT}Enabled" in a and a[-1] == "true"
               and "Plugins" in a for a in writes), writes


def test_uninstall_removes_and_disables_the_script(tmp_path, monkeypatch):
    writes: list[tuple] = []
    wd = _patch_step(monkeypatch, tmp_path, writes)
    wd.install()
    writes.clear()
    wd.uninstall()

    assert not (tmp_path / "kwin/scripts" / wd.FULLSCREEN_SCRIPT).exists()
    assert any(f"{wd.FULLSCREEN_SCRIPT}Enabled" in a and "--delete" in a
               for a in writes), writes


GLOBALMENU = REPO / "src/offline/plasmoids/org.kde.mac.tahoe.liquid.globalmenu"


def test_menu_bar_has_no_traffic_lights():
    """macOS no longer puts a full screen window's traffic lights in the menu
    bar: leaving full screen goes through Ctrl+Meta+F or the window menu."""
    assert not (GLOBALMENU / "qml/WindowLights.qml").exists()
    assert "WindowLights" not in (GLOBALMENU / "qml/main.qml").read_text()
    assert "WindowLights" not in (GLOBALMENU / "CMakeLists.txt").read_text()
    applet = (GLOBALMENU / "appmenuapplet.cpp").read_text()
    assert 'i18n("Exit Full Screen")' in applet


def test_install_sets_up_the_macos_app_switcher(tmp_path, monkeypatch):
    """Alt+Tab is the macOS switcher: our KWin layout, one entry per app,
    no window highlighting; uninstall gives KWin's back only if ours is in
    use."""
    from steps import window_decorations as wd

    writes: list[tuple] = []
    wd = _patch_step(monkeypatch, tmp_path, writes)
    real = Path(__file__).resolve().parents[1] / "src/offline/kwin-tabbox" / wd.SWITCHER
    fake = tmp_path / "offline/kwin-tabbox" / wd.SWITCHER
    shutil.copytree(real, fake)
    monkeypatch.setattr(wd, "TABBOX_DIR", tmp_path / "kwin/tabbox")
    wd.install()
    assert (tmp_path / "kwin/tabbox" / wd.SWITCHER / "contents/ui/main.qml").is_file()
    for key, value in (("LayoutName", wd.SWITCHER), ("ApplicationsMode", "1"),
                       ("HighlightWindows", "false")):
        assert any("TabBox" in a and key in a and a[-1] == value for a in writes), key

    qml = (real / "contents/ui/main.qml").read_text()
    assert "KWin.TabBoxSwitcher {" in qml and "orientation: ListView.Horizontal" in qml
    assert "Math.min(96," in qml  # 96 px icons, smaller only when they would not fit
    assert "import org.kde.mac" not in qml  # nothing compiled of ours inside KWin

    writes.clear()
    monkeypatch.setattr(wd, "kw_read", lambda *_a: wd.SWITCHER)
    wd.uninstall()
    assert not (tmp_path / "kwin/tabbox" / wd.SWITCHER).exists()
    assert any("TabBox" in a and "LayoutName" in a and a[-1] == "--delete" for a in writes)


def test_install_leaves_the_top_left_corner_to_the_apple_menu(tmp_path, monkeypatch):
    """KWin's Overview hot corner sits where the Apple menu is: install
    turns it off (KWin's ElectricNone), unless the user picked a corner;
    uninstall gives KWin's default back only if the value is still ours."""
    writes: list[tuple] = []
    wd = _patch_step(monkeypatch, tmp_path, writes)
    wd.install()
    assert ("--file", "kwinrc", "--group", "Effect-overview",
            "--key", "BorderActivate", "9") in writes

    writes.clear()
    monkeypatch.setattr(wd, "kw_read", lambda file, group, key:
                        "3" if (group, key) == ("Effect-overview", "BorderActivate") else "")
    wd.install()
    assert not any("Effect-overview" in a for a in writes), writes
    wd.uninstall()
    assert not any("Effect-overview" in a for a in writes), writes

    monkeypatch.setattr(wd, "kw_read", lambda file, group, key:
                        "9" if (group, key) == ("Effect-overview", "BorderActivate") else "")
    wd.uninstall()
    assert ("--file", "kwinrc", "--group", "Effect-overview",
            "--key", "BorderActivate", "--delete") in writes
