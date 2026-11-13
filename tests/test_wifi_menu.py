"""The macOS Wi-Fi menu bar item (org.kde.mac-tahoe-liquid-kde.wifi): the
plasma-nm backend shown as the Tahoe Wi-Fi menu, in place of the network
applet the tray keeps hidden."""

import json

WIDGET = "plasmoids/org.kde.mac-tahoe-liquid-kde.wifi"


def test_metadata(offline):
    meta = json.loads((offline / WIDGET / "metadata.json").read_text())
    assert meta["KPlugin"]["Id"] == "org.kde.mac-tahoe-liquid-kde.wifi"
    assert meta["KPackageStructure"] == "Plasma/Applet"


def test_menu_is_a_floating_popover(offline):
    main = (offline / WIDGET / "contents/ui/main.qml").read_text()
    assert "location: PlasmaCore.Types.Floating" in main
    assert "fullRepresentation: Item {}" in main
    assert "PlasmaNM.ConnectionIcon" in main


def test_menu_follows_the_capture(offline):
    view = (offline / WIDGET / "contents/ui/WifiView.qml").read_text()
    for text in ('"Wi-Fi"', '"Known Networks"', '"Other Networks"', '"Wi-Fi Settings…"'):
        assert text in view, text
    # The switch, the current non-Wi-Fi connections, then the networks; the
    # other networks fold behind their row (wifi.jpg, macOS Tahoe).
    assert view.index("MacSwitch {") < view.index("model: view.current") \
        < view.index("model: view.wifiOn ? view.known : []") \
        < view.index("model: view.wifiOn && view.othersOpen ? view.others : []")
    assert "property bool othersOpen: false" in view
    assert "onClicked: view.othersOpen = !view.othersOpen" in view
    assert "component Separator: Rectangle {" in view
    # The Tahoe switch: a 50 x 24 pill and a 30 x 20 capsule.
    assert "implicitWidth: 50" in view and "width: 30\n            height: 20" in view
    # Saved networks connect, new secured ones ask for a password first.
    assert "handler.activateConnection(" in view
    assert "handler.addAndActivateConnection(network.devicePath, network.specificPath, password)" in view
    assert 'KCMUtils.KCMLauncher.openSystemSettings("kcm_networkmanagement")' in view
