/*
    AquaDesktop — round Control Center toggle or action.

    On its own it is a glass bubble like every module; inside a tile
    (bubble: false) it is a plain disc. Active toggles are a white disc
    under a glyph in the accent colour (`activeColor`), as on macOS Tahoe.

    SPDX-License-Identifier: GPL-3.0-or-later
*/
import QtQuick

import org.kde.kirigami as Kirigami
import "Palette.js" as Palette

Item {
    id: button

    property string glyph
    property bool active: false
    property color activeColor: Kirigami.Theme.highlightColor
    property string toolTip
    // Reference Control Center: 26-30 px glyphs in 64 px circles
    // bubbles (the calculator 22 x 30, Stage Manager 29 x 22).
    property real glyphScale: 0.48
    property bool bubble: true
    // GlassBlur blurs the desktop behind a bubble; a disc inside a tile is
    // already on glass.
    readonly property real glassRadius: bubble ? width / 2 : -1
    readonly property bool dark: Palette.isDark(Kirigami.Theme.textColor)

    signal clicked()

    implicitWidth: 70
    implicitHeight: 70
    opacity: enabled ? 1 : 0.4

    Accessible.role: Accessible.Button
    Accessible.name: toolTip
    Accessible.checked: active

    Rectangle {
        id: disc

        anchors.fill: parent
        radius: width / 2
        color: {
            if (button.active) {
                return "white";
            }
            if (button.bubble) {
                // The glass face is GlassSurface below.
                return "transparent";
            }
            return Palette.innerDisc(button.dark, area.containsMouse);
        }
        scale: area.pressed ? 0.94 : 1

        Behavior on color {
            ColorAnimation { duration: Kirigami.Units.shortDuration }
        }
        Behavior on scale {
            NumberAnimation { duration: Kirigami.Units.shortDuration; easing.type: Easing.OutCubic }
        }

        GlassSurface {
            anchors.fill: parent
            radius: width / 2
            hovered: area.containsMouse
            visible: button.bubble && !button.active
        }

        Glyph {
            anchors.centerIn: parent
            width: Math.round(parent.width * button.glyphScale)
            height: width
            glyph: button.glyph
            color: button.active ? button.activeColor : Kirigami.Theme.textColor
        }
    }

    MouseArea {
        id: area

        anchors.fill: parent
        hoverEnabled: true
        onClicked: button.clicked()
    }
}
