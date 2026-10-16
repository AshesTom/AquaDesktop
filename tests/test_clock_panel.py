"""The menu bar clock's panel, measured on the reference macOS Tahoe
capture: notifications, the date card and two clocks in glass bubbles."""

UI = "plasmoids/org.kde.mac-tahoe-liquid-kde.clock/contents/ui"


def test_clock_opens_the_macos_panel_not_plasmas_calendar(offline):
    main = (offline / UI / "main.qml").read_text()
    assert "PlasmaCalendar" not in main
    assert "fullRepresentation: Item {}" in main
    assert "onClicked: root.togglePanel()" in main
    assert "backgroundHints: PlasmaCore.Dialog.NoBackground" in main
    # 12 px from the right edge, the first bubble 34 px from the top.
    assert "readonly property int panelMargin: 12" in main
    assert "panel.x = screen.x + screen.width - width - panelMargin;" in main
    assert "readonly property int glassPad: 28" in main
    assert 'source: "WindowBlur.qml"' in main


def test_panel_geometry_follows_the_capture(offline):
    view = (offline / UI / "ClockPanelView.qml").read_text()
    assert "implicitWidth: 356" in view
    assert "height: 46" in view and "radius: 23" in view           # empty pill
    assert "height: 168" in view                                    # date card
    assert "x: 176 + (cell % 7) * 25 - width / 2" in view           # 25 px columns
    assert "y: 65 + Math.floor(cell / 7) * 18 - height / 2" in view  # 18 px rows
    assert 'readonly property color red: "#ff453a"' in view
    assert "height: 170" in view and "spacing: 12" in view          # clocks
    assert "Qt.locale().firstDayOfWeek" in view
    # No Plasmoid API: the view also works outside Plasma.
    assert "import org.kde.plasma.plasmoid" not in view and "Plasmoid." not in view
    notifications = (offline / UI / "NotificationList.qml").read_text()
    assert "NotificationManager.Notifications {" in notifications
    assert "readonly property int count: bubbles.count" in notifications
    card = (offline / UI / "GlassCard.qml").read_text()
    assert "readonly property real glassRadius: radius" in card
