/*
    AquaDesktop shell — the macOS menu bar of one screen.

    Left: the Apple menu, the active app's name and its menus.
    Right, as on macOS: the status items (the system tray's
    StatusNotifierItems), Wi-Fi, Spotlight, Control Center and the clock.
    No background in the Tahoe style: white text and glyphs over the
    wallpaper, 13 px text, extras on a 36 px pitch.

    SPDX-License-Identifier: GPL-3.0-or-later
*/
import QtQuick
import QtQuick.Layouts
import Quickshell
import Quickshell.Wayland
import Quickshell.Widgets
import Quickshell.Services.SystemTray
import org.kde.kirigami as Kirigami
import "views/controlcenter" as CC

PanelWindow {
    id: bar

    // Which popover is open ("" for none), owned by shell.qml.
    property string openPopover: ""
    readonly property int barHeight: 30
    readonly property color ink: "white"

    // Where a popover opened from `item` goes (its centre, kept on screen).
    signal toggleRequested(string name, real centerX)

    anchors {
        top: true
        left: true
        right: true
    }
    implicitHeight: barHeight
    exclusiveZone: barHeight
    color: "transparent"

    WlrLayershell.layer: WlrLayer.Top
    WlrLayershell.namespace: "dock"

    // Opens menu `index` of the app menus (AppMenuBar.activate()).
    function openMenu(index: int): void {
        if (appMenus.item) {
            appMenus.item.activate(index);
        }
    }

    function centerOf(item: Item): real {
        return item.mapToItem(null, item.width / 2, 0).x;
    }

    // The Apple menu and the active app's menus (AppMenuBar.qml); just the
    // logo when the compiled appmenu module is missing.
    Loader {
        id: appMenus
        anchors {
            left: parent.left
            leftMargin: 10
            top: parent.top
            bottom: parent.bottom
        }
        source: "AppMenuBar.qml"
        onLoaded: item.ink = Qt.binding(() => bar.ink)
    }
    Image {
        visible: appMenus.status === Loader.Error
        anchors {
            left: parent.left
            leftMargin: 18
            verticalCenter: parent.verticalCenter
        }
        source: "assets/apple-logo.svg"
        sourceSize: Qt.size(14, 17)
        width: 14
        height: 17
    }

    RowLayout {
        anchors {
            right: parent.right
            rightMargin: 14
            verticalCenter: parent.verticalCenter
        }
        spacing: 0

        Repeater {
            model: SystemTray.items
            delegate: Extra {
                id: trayItem
                required property SystemTrayItem modelData
                visible: modelData.status !== Status.Passive
                IconImage {
                    anchors.centerIn: parent
                    implicitSize: 18
                    source: trayItem.modelData.icon
                }
                onClicked: mouse => {
                    if (mouse.button === Qt.RightButton || trayItem.modelData.onlyMenu) {
                        menuAnchor.open();
                    } else {
                        trayItem.modelData.activate();
                    }
                }
                QsMenuAnchor {
                    id: menuAnchor
                    menu: trayItem.modelData.menu
                    anchor.item: trayItem
                    anchor.edges: Edges.Bottom
                }
            }
        }

        Extra {
            id: wifiButton
            highlighted: bar.openPopover === "wifi"
            onClicked: bar.toggleRequested("wifi", bar.centerOf(wifiButton))
            CC.Glyph {
                anchors.centerIn: parent
                width: 18
                height: 18
                glyph: "wifi"
                color: bar.ink
            }
        }
        Extra {
            id: searchButton
            highlighted: bar.openPopover === "spotlight"
            onClicked: bar.toggleRequested("spotlight", bar.centerOf(searchButton))
            Kirigami.Icon {
                anchors.centerIn: parent
                width: 16
                height: 16
                source: "system-search-symbolic"
                isMask: true
                color: bar.ink
            }
        }
        Extra {
            id: controlCenterButton
            highlighted: bar.openPopover === "controlcenter"
            onClicked: bar.toggleRequested("controlcenter", bar.centerOf(controlCenterButton))
            CC.Glyph {
                anchors.centerIn: parent
                width: 18
                height: 18
                glyph: "controlcenter"
                color: bar.ink
            }
        }

        Text {
            Layout.leftMargin: 8
            color: bar.ink
            font.pixelSize: 13
            // macOS: "Sat Oct 3 14:24", in the user's locale.
            text: Qt.locale().toString(clock.date, "ddd d MMM") + "  "
                  + Qt.locale().toString(clock.date, Qt.locale().timeFormat(Locale.ShortFormat))
            SystemClock {
                id: clock
                precision: SystemClock.Minutes
            }
        }
    }

    // A menu bar extra: 36 px wide, highlighted only while its menu is open.
    component Extra: MouseArea {
        id: extra

        property bool highlighted: false

        Layout.preferredWidth: 36
        Layout.fillHeight: true
        acceptedButtons: Qt.LeftButton | Qt.RightButton

        Rectangle {
            anchors.centerIn: parent
            width: 30
            height: 22
            radius: 6
            color: Qt.rgba(1, 1, 1, 0.22)
            visible: extra.highlighted
        }
    }
}
