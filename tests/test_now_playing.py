"""Now Playing in the menu bar, and no audio badge in the Dock (MacTahoe Liquid KDE)."""

import json
import re

ROOT = "plasmoids/org.kde.mac-tahoe-liquid-kde.nowplaying"
LAYOUTS = (
    "layouts/mac-tahoe.js",
    "look-and-feel/MacTahoeLiquidKde-Dark/contents/layouts/org.kde.plasma.desktop-layout.js",
    "look-and-feel/MacTahoeLiquidKde-Light/contents/layouts/org.kde.plasma.desktop-layout.js",
)


def test_is_a_menu_bar_item_right_before_the_tray(offline):
    """Not a tray item: the tray shows applets in its own fixed-width popup
    with a heading, where macOS shows a small popover."""
    meta = json.loads((offline / ROOT / "metadata.json").read_text())
    assert meta["KPlugin"]["Id"] == "org.kde.mac-tahoe-liquid-kde.nowplaying"
    assert "X-Plasma-NotificationArea" not in meta
    for layout in LAYOUTS:
        text = (offline / layout).read_text()
        now = text.index('addWidget("org.kde.mac-tahoe-liquid-kde.nowplaying")')
        tray = text.index('var tray = bar.addWidget(')
        assert now < tray
        extra = re.search(r'writeConfig\("extraItems", "([^"]+)"\)', text).group(1)
        assert "nowplaying" not in extra


def test_only_shows_up_while_a_player_is_around(offline):
    main = (offline / ROOT / "contents/ui/main.qml").read_text()
    assert "Mpris.Mpris2Model" in main
    assert ("Plasmoid.status: hasPlayer ? PlasmaCore.Types.ActiveStatus"
            " : PlasmaCore.Types.HiddenStatus") in main
    assert 'glyph: "play-circle"' in main
    assert "preferredRepresentation: compactRepresentation" in main


def test_popover_floats_fully_rounded_under_the_menu_bar(offline):
    """Plasma glues applet popups to a non-floating panel (square top corners
    under the bar); macOS floats a rounded rectangle a few pixels below."""
    main = (offline / ROOT / "contents/ui/main.qml").read_text()
    assert "PlasmaCore.Dialog {" in main
    assert "location: PlasmaCore.Types.Floating" in main
    assert "fullRepresentation: Item {}" in main
    assert "popover.y = Math.round(origin.y + anchor.height + popoverGap);" in main
    assert "readonly property int popoverGap: 6" in main
    # A global shortcut opens the popover too.
    assert "function onActivated(): void" in main


def test_popup_follows_the_macos_layout(offline):
    view = (offline / ROOT / "contents/ui/NowPlayingView.qml").read_text()
    assert "implicitWidth: 270" in view
    # No progress row when the player publishes no length.
    assert "implicitHeight: hasProgress ? 115 : 89" in view
    assert "readonly property bool hasProgress: length > 0" in view
    # The position stays bound to the player; polling only refreshes it.
    assert "readonly property real position: player ? player.position : 0" in view
    assert "onTriggered: view.player.updatePosition()" in view
    assert "width: 50" in view and "height: 50" in view
    assert "spacing: 45 - 28" in view
    assert "view.player.position = target" in view
    assert re.search(r'glyph: view\.playing \? "pause" : "play"', view)


def test_translations(offline):
    import gettext
    for language, expected in (("es", "En reproducción"), ("zh_CN", "正在播放")):
        mo = (offline / ROOT / "contents/locale" / language / "LC_MESSAGES"
              / "plasma_applet_org.kde.mac-tahoe-liquid-kde.nowplaying.mo")
        with mo.open("rb") as stream:
            assert gettext.GNUTranslations(stream).pgettext("@title", "Now Playing") == expected


def test_dock_draws_no_audio_badge_by_default(offline):
    xml = (offline / "plasmoids/org.kde.mac.tahoe.liquid.taskmanager/contents/config/main.xml").read_text()
    entry = xml[xml.index('<entry name="indicateAudioStreams"'):]
    entry = entry[:entry.index("</entry>")]
    assert "<default>false</default>" in entry
