/*
    AquaDesktop — the macOS Tahoe switch, measured at 1x: a 36 x 16
    capsule track (accent when on) and a 22 x 14 light capsule knob inset by
    1 px, which slides to the end that is on.

    SPDX-License-Identifier: GPL-3.0-or-later
*/
import QtQuick
import QtQuick.Templates as T
import org.kde.kirigami as Kirigami

Item {
    id: indicator

    property T.AbstractButton control

    implicitWidth: 36
    implicitHeight: 16
    opacity: control && control.enabled ? 1 : 0.5

    Rectangle {
        id: track
        anchors.fill: parent
        radius: height / 2
        color: indicator.control && indicator.control.checked
            ? Kirigami.Theme.highlightColor
            : Qt.rgba(Kirigami.Theme.textColor.r, Kirigami.Theme.textColor.g,
                      Kirigami.Theme.textColor.b, 0.20)
        Behavior on color {
            enabled: Kirigami.Units.shortDuration > 0
            ColorAnimation { duration: Kirigami.Units.shortDuration }
        }
    }

    Rectangle {
        id: knob
        y: 1
        width: 22
        height: parent.height - 2
        radius: height / 2
        x: 1 + (indicator.control ? indicator.control.visualPosition : 0) * (parent.width - width - 2)
        color: indicator.control && indicator.control.pressed ? "#D8D8D8" : "#EDEDED"
        border.width: 0.5
        border.color: Qt.rgba(0, 0, 0, 0.12)

        Behavior on x {
            enabled: indicator.control && !indicator.control.pressed && Kirigami.Units.shortDuration > 0
            SmoothedAnimation { duration: Kirigami.Units.shortDuration }
        }
    }
}
