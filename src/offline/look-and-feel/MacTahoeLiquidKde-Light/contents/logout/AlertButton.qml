/*
    AquaDesktop — a macOS alert button: a capsule filling its row, the
    default one in the accent colour with white text.

    SPDX-License-Identifier: GPL-3.0-or-later
*/
import QtQuick

import org.kde.kirigami as Kirigami

Item {
    id: button

    property string text
    property bool isDefault: false
    property bool dark: false
    property color accent: Kirigami.Theme.highlightColor

    signal clicked()

    implicitHeight: 28
    implicitWidth: Math.max(96, label.implicitWidth + 32)

    Accessible.role: Accessible.Button
    Accessible.name: text
    Accessible.onPressAction: button.clicked()

    Rectangle {
        anchors.fill: parent
        radius: height / 2
        color: {
            if (button.isDefault) {
                return mouse.pressed ? Qt.darker(button.accent, 1.15) : button.accent;
            }
            const base = button.dark ? Qt.rgba(1, 1, 1, 0.12) : Qt.rgba(0, 0, 0, 0.06);
            return mouse.pressed ? (button.dark ? Qt.rgba(1, 1, 1, 0.22) : Qt.rgba(0, 0, 0, 0.14)) : base;
        }
    }

    Text {
        id: label
        anchors.centerIn: parent
        width: Math.min(implicitWidth, parent.width - 16)
        elide: Text.ElideRight
        text: button.text
        textFormat: Text.PlainText
        font: Kirigami.Theme.defaultFont
        color: button.isDefault ? "white" : Kirigami.Theme.textColor
        renderType: Text.NativeRendering
    }

    MouseArea {
        id: mouse
        anchors.fill: parent
        onClicked: button.clicked()
    }
}
