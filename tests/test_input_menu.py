"""The macOS Input menu (org.kde.mac-tahoe-liquid-kde.keyboard): the keyboard
layout's letters cut out of a white box in the menu bar, and the Input menu
measured on the reference capture."""

import gettext
import json
import os
import shutil
import subprocess

import pytest

WIDGET = "plasmoids/org.kde.mac-tahoe-liquid-kde.keyboard"
UI = WIDGET + "/contents/ui"
DOMAIN = "plasma_applet_org.kde.mac-tahoe-liquid-kde.keyboard"


def test_metadata(offline):
    meta = json.loads((offline / WIDGET / "metadata.json").read_text())
    assert meta["KPlugin"]["Id"] == "org.kde.mac-tahoe-liquid-kde.keyboard"
    assert meta["KPackageStructure"] == "Plasma/Applet"
    assert meta["KPlugin"]["Name[fr]"] == "Menu Saisie (MacTahoe Liquid KDE)"


def test_extra_shows_only_with_several_layouts(offline):
    main = (offline / UI / "main.qml").read_text()
    # Plasma's own layouts (KWin's org.kde.keyboard on Wayland).
    assert "import org.kde.plasma.workspace.keyboardlayout as Keyboards" in main
    assert "Keyboards.KeyboardLayout {" in main
    # macOS shows the Input menu once a second input source exists.
    assert ("Plasmoid.status: layouts.length > 1 ? PlasmaCore.Types.ActiveStatus"
            " : PlasmaCore.Types.HiddenStatus") in main
    # No tooltip over the menu, like the other extras.
    assert 'toolTipMainText: ""' in main
    # "fr" -> "FR"; a label set in Keyboard Settings is kept.
    assert "String(currentLayout.shortName).toUpperCase()" in main
    assert "currentLayout.displayName ? currentLayout.displayName" in main


def test_menu_is_a_glass_popover_left_aligned_on_the_extra(offline):
    main = (offline / UI / "main.qml").read_text()
    assert "location: PlasmaCore.Types.Floating" in main
    assert "backgroundHints: PlasmaCore.Dialog.NoBackground" in main
    assert "fullRepresentation: Item {}" in main
    assert "readonly property int glassPad: 28" in main
    assert 'source: "WindowBlur.qml"' in main
    assert "readonly property real glassRadius: 14" in main
    # A macOS menu starts at its extra's left edge, kept on screen.
    assert "let x = Math.round(origin.x);" in main


def test_icon_is_the_measured_template_box(offline):
    icon = (offline / UI / "InputSourceIcon.qml").read_text()
    # 20 x 18 px, 5 px corners, bold capitals 9 px tall, cut out.
    for line in ("int boxHeight: 18", "int minimumWidth: 20", "real radius: 5", "real capHeight: 9"):
        assert f"readonly property {line}" in icon, line
    assert 'c.globalCompositeOperation = "destination-out";' in icon
    assert "font.weight: Font.Bold" in icon
    # Context2D keeps the generic family when it refuses the system one.
    assert icon.index('px sans-serif"') < icon.index('metrics.font.family + "\\""')


def test_menu_follows_the_capture(offline):
    view = (offline / UI / "KeyboardView.qml").read_text()
    entries = ('"Show Emoji & Symbols"', '"Show Keyboard Viewer"',
               '"Show Clipboard History"', '"Open Keyboard Settings…"')
    positions = [view.index(text) for text in entries]
    assert view.index("model: view.layouts") < positions[0]
    assert positions == sorted(positions)
    assert "implicitWidth: Math.max(278, column.widest)" in view
    assert "readonly property int rowHeight: 24" in view
    # The check mark 14 px in, the layouts 32 px in, the rest 18 px in.
    assert "x: entry.checkable ? 32 : 18" in view
    assert 'text: "✓"' in view
    assert "anchors.rightMargin: 16" in view
    # The accent highlight, 8 px corners.
    assert "AccentColor {" in view and "radius: 8" in view
    # No Plasmoid API: the view renders on its own.
    assert "org.kde.plasma.plasmoid" not in view


def test_menu_actions_reach_kde_tools(offline):
    main = (offline / UI / "main.qml").read_text()
    assert "onLayoutRequested: index => keyboardLayout.layout = index" in main
    assert 'executable.connectSource("plasma-emojier")' in main
    assert 'executable.connectSource("systemsettings kcm_keyboard")' in main
    # The keyboard viewer gets the layout's XKB names, filtered for the shell.
    assert 'let command = "tastenbrett --model " + model + " --layout " + layout;' in main
    assert 'replace(/[^A-Za-z0-9_+-]/g, "")' in main
    assert '" || systemsettings kcm_keyboard"' in main
    # Klipper's menu once this one has closed.
    assert 'path: "/component/plasmashell"' in main
    assert 'arguments: ["show-on-mouse-pos"]' in main
    assert "onClipboardRequested: clipboardTimer.start()" in main


def test_layouts_add_the_extra_before_sound(offline):
    for relative in ("layouts/mac-tahoe.js",
                     "look-and-feel/MacTahoeLiquidKde-Dark/contents/layouts/org.kde.plasma.desktop-layout.js",
                     "look-and-feel/MacTahoeLiquidKde-Light/contents/layouts/org.kde.plasma.desktop-layout.js"):
        script = (offline / relative).read_text()
        keyboard = script.index('addWidget("org.kde.mac-tahoe-liquid-kde.keyboard")')
        assert keyboard < script.index('addWidget("org.kde.mac-tahoe-liquid-kde.volume")'), relative
        # Plasma's layout applet stays hidden in the tray.
        assert "org.kde.plasma.keyboardlayout" in script


@pytest.mark.parametrize("language,expected", [
    ("es", ("Mostrar emojis y símbolos", "Espacio")),
    ("fr", ("Afficher Emoji et symboles", "Espace")),
    ("zh_CN", ("显示表情与符号", "空格")),
])
def test_translations_ship(offline, language, expected):
    mo = offline / WIDGET / "contents/locale" / language / "LC_MESSAGES" / f"{DOMAIN}.mo"
    with mo.open("rb") as stream:
        catalog = gettext.GNUTranslations(stream)
    assert catalog.pgettext("@action Input menu", "Show Emoji & Symbols") == expected[0]
    assert catalog.pgettext("@item:keyboard the space bar, as macOS menus name it", "Space") == expected[1]


def test_shortcuts_are_drawn_the_macos_way(offline, tmp_path):
    """Runs the view's macShortcut() in an offscreen QML engine."""
    qml = shutil.which("qml6") or shutil.which("qml")
    if not qml:
        pytest.skip("no QML runtime")
    probe = tmp_path / "probe.qml"
    probe.write_text(f"""
import QtQuick
import "file://{offline / UI}"
Item {{
    KeyboardView {{ id: view }}
    Component.onCompleted: {{
        for (const s of ["Meta+.", "Ctrl+Shift+N", "Meta+V\\tCtrl+Alt+V", "Ctrl+Meta+Space", "none", "", "Ctrl++"])
            console.log("SHORTCUT[" + view.macShortcut(s) + "]");
        Qt.quit();
    }}
}}
""")
    env = {
        **os.environ,
        "QT_QPA_PLATFORM": "offscreen",
        "QT_FORCE_STDERR_LOGGING": "1",
        "LANGUAGE": "en",
        "XDG_CONFIG_HOME": str(tmp_path / "config"),
        "XDG_DATA_HOME": str(tmp_path / "data"),
        "XDG_CACHE_HOME": str(tmp_path / "cache"),
    }
    env.pop("WAYLAND_DISPLAY", None)
    env.pop("DISPLAY", None)
    result = subprocess.run([qml, str(probe)], env=env, capture_output=True, text=True, timeout=60)
    found = [line.split("SHORTCUT[", 1)[1].rsplit("]", 1)[0]
             for line in result.stderr.splitlines() if "SHORTCUT[" in line]
    if not found and "is not installed" in result.stderr:
        pytest.skip("Kirigami / KI18n QML modules missing")
    assert found == ["⌃.", "⇧⌘N", "⌃V", "⌃⌘Space", "", "", "⌘+"], result.stderr
