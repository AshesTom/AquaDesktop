"""Spotlight (org.kde.mac-tahoe-liquid-kde.spotlight): the macOS Tahoe
search pill, its four buttons and the KRunner results panel, in place of
KRunner's own window."""

UI = "plasmoids/org.kde.mac-tahoe-liquid-kde.spotlight/contents/ui"


def test_opens_spotlight_and_falls_back_to_krunner(offline):
    main = (offline / UI / "main.qml").read_text()
    assert 'source: "SpotlightView.qml"' in main
    assert 'executable.connectSource("krunner")' in main  # without Milou
    assert "backgroundHints: PlasmaCore.Dialog.NoBackground" in main
    assert "screen.height * 0.2" in main
    assert 'source: "WindowBlur.qml"' in main


def test_view_follows_the_capture(offline):
    view = (offline / UI / "SpotlightView.qml").read_text()
    assert "import org.kde.milou as Milou" in view
    assert "Milou.ResultsModel {" in view
    # 448 px pill, 56 px buttons 12 px apart, a 720 px panel, 44 px rows.
    assert "implicitWidth: 720" in view and "readonly property int rowHeight: 44" in view
    assert "width: expanded ? view.width : 448" in view
    assert "width: 56" in view and "spacing: 12" in view
    for runner in ("krunner_services", "baloosearch", "krunner_systemsettings"):
        assert f'runner: "{runner}"' in view
    # Keyboard: arrows move, Return runs, Escape clears then closes.
    for key in ("Qt.Key_Down", "Qt.Key_Up", "Qt.Key_Return", "Qt.Key_Escape"):
        assert key in view


def test_window_never_resizes_while_typing(offline):
    """A resize makes Plasma's Dialog drop the window's blur, which then
    flickers off and on with every result: the window keeps the panel's
    tallest size and only the glass shapes change."""
    main = (offline / UI / "main.qml").read_text()
    view = (offline / UI / "SpotlightView.qml").read_text()
    assert "height: spotlight.item ? spotlight.item.maxHeight + 2 * root.glassPad : 0" in main
    assert "readonly property int maxHeight: 60 + 9 + maxRows * rowHeight + 10" in view
    assert "onHeightChanged: view.glassChanged()" in view
    assert "function onGlassChanged(): void" in main


def test_blur_is_asked_again_after_the_popup_shows(offline):
    for widget in ("spotlight", "controlcenter"):
        ui = offline / f"plasmoids/org.kde.mac-tahoe-liquid-kde.{widget}/contents/ui"
        assert "active: popover.visible" in (ui / "main.qml").read_text()
        settler = (ui / "BlurSettler.qml").read_text()
        assert "readonly property var delays: [0, 60, 140, 300, 700, 1200]" in settler
    glass = (offline / "qml/org.kde.mac.tahoe.liquid.glass/glassblur.cpp").read_text()
    assert "kSettleDelays" in glass and "m_window->setMask(region)" in glass
