/*
    AquaDesktop — the macOS application switcher (Cmd+Tab), as KWin's
    window switcher layout: one row of 96 px app icons on the theme's glass
    panel, centred on the screen; the selected app sits on a rounded
    square, its name below the row. kwinrc [TabBox] ApplicationsMode=1
    makes it one entry per application, like macOS.

    It runs inside KWin, so it only uses Plasma's own QML modules (no
    compiled module of ours).

    SPDX-License-Identifier: GPL-3.0-or-later
*/
import QtQuick
import org.kde.plasma.core as PlasmaCore
import org.kde.kirigami as Kirigami
import org.kde.plasma.components as PlasmaComponents3
import org.kde.kwin as KWin

KWin.TabBoxSwitcher {
    id: tabBox

    currentIndex: (instantiator.object as SwitcherDialog)?.currentIndex ?? currentIndex

    // The application's name from a window title ("Page — App" in KDE and
    // most apps), as macOS names the selected app.
    function appName(caption: string): string {
        const parts = caption.split(/ [—–-] /);
        return parts.length > 1 ? parts[parts.length - 1] : caption;
    }

    Instantiator {
        id: instantiator
        active: tabBox.visible
        delegate: SwitcherDialog {}
    }

    component SwitcherDialog: PlasmaCore.Dialog {
        property alias currentIndex: icons.currentIndex

        location: PlasmaCore.Types.Floating
        visible: tabBox.visible
        flags: Qt.Popup | Qt.X11BypassWindowManagerHint
        x: tabBox.screenGeometry.x + Math.round((tabBox.screenGeometry.width - width) / 2)
        y: tabBox.screenGeometry.y + Math.round((tabBox.screenGeometry.height - height) / 2)

        mainItem: Item {
            id: content

            readonly property int count: icons.count
            // Smaller icons when the row would not fit in 90 % of the screen.
            readonly property int iconSize: Math.max(48, Math.min(96,
                Math.floor(tabBox.screenGeometry.width * 0.9 / Math.max(1, count)) - 20))
            readonly property int cell: iconSize + 20

            width: Math.max(cell, icons.contentWidth) + 8
            height: cell + name.implicitHeight + 14

            ListView {
                id: icons

                x: 4
                y: 2
                width: contentWidth
                height: content.cell
                orientation: ListView.Horizontal
                interactive: false
                focus: true
                keyNavigationWraps: true
                model: tabBox.model
                currentIndex: tabBox.currentIndex
                highlightMoveDuration: 0

                // The selection: a rounded square of light glass.
                highlight: Rectangle {
                    width: content.cell
                    height: content.cell
                    radius: Math.round(content.cell * 0.18)
                    color: Qt.rgba(Kirigami.Theme.textColor.r, Kirigami.Theme.textColor.g,
                                   Kirigami.Theme.textColor.b, 0.16)
                }

                delegate: Item {
                    required property int index
                    required property var model

                    width: content.cell
                    height: content.cell

                    Kirigami.Icon {
                        anchors.centerIn: parent
                        width: content.iconSize
                        height: content.iconSize
                        source: parent.model.icon
                        roundToIconSize: false
                    }
                    TapHandler {
                        onSingleTapped: {
                            if (parent.index === icons.currentIndex) {
                                icons.model.activate(parent.index);
                            } else {
                                icons.currentIndex = parent.index;
                            }
                        }
                        onDoubleTapped: icons.model.activate(parent.index)
                    }
                }

                Connections {
                    target: tabBox
                    function onCurrentIndexChanged(): void {
                        icons.currentIndex = tabBox.currentIndex;
                    }
                }
            }

            PlasmaComponents3.Label {
                id: name

                anchors.horizontalCenter: parent.horizontalCenter
                y: icons.y + icons.height + 4
                width: parent.width - 16
                horizontalAlignment: Text.AlignHCenter
                elide: Text.ElideRight
                textFormat: Text.PlainText
                font.pixelSize: 13
                text: icons.currentItem ? tabBox.appName(icons.currentItem.model.caption) : ""
            }

            Kirigami.PlaceholderMessage {
                anchors.centerIn: parent
                width: parent.width
                visible: icons.count === 0
                text: i18ndc("kwin", "@info:placeholder no entries in the task switcher", "No open windows")
            }

            Keys.onPressed: event => {
                if (event.key === Qt.Key_Left) {
                    icons.decrementCurrentIndex();
                } else if (event.key === Qt.Key_Right) {
                    icons.incrementCurrentIndex();
                }
            }
        }

        onSceneGraphError: () => {
            // Left blank: otherwise QtQuick may qFatal() on a graphics reset.
        }
    }
}
