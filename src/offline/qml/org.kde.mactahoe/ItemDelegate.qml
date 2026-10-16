/*
    AquaDesktop — macOS list rows for Kirigami / Qt Quick apps.

    org.kde.desktop's delegate, with macOS' selection: the selected row is
    filled with the accent colour, 6 px rounded and inset from the list
    edges, with white text; hovering draws nothing, like System Settings'
    and Mail's sidebars.

    SPDX-License-Identifier: GPL-3.0-or-later
*/
import QtQuick
import org.kde.kirigami as Kirigami
import org.kde.desktop as Desktop

Desktop.ItemDelegate {
    id: control

    background: Item {
        Rectangle {
            anchors.fill: parent
            radius: 6
            color: Kirigami.Theme.highlightColor
            visible: control.highlighted || control.down || control.checked
            opacity: control.down && !control.highlighted ? 0.6 : 1
        }
    }
}
