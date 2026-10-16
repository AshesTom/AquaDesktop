/*
    AquaDesktop — full-width Control Center slider (Display, Sound), as on
    the macOS Tahoe capture: a 70 px bubble like the other modules, the
    title 20 px down, then a 9 px bar 45 px down between a small glyph at
    each end; the white fill has no knob. Sound ends with a round
    accessory (AirPlay) after its loud glyph.

    SPDX-License-Identifier: GPL-3.0-or-later
*/
import QtQuick

import org.kde.kirigami as Kirigami
import "Palette.js" as Palette

Tile {
    id: tile

    property string title
    property string leadingGlyph
    property string trailingGlyph
    property string accessoryGlyph
    property string accessoryToolTip
    // 0..1
    property real value: 0
    readonly property bool dark: Palette.isDark(Kirigami.Theme.textColor)

    signal moved(real value)
    signal accessoryClicked()

    // Apple's Display and Sound: 29 px corners on an 84 px bubble.
    radius: 24
    implicitWidth: 292
    implicitHeight: 64

    Text {
        id: label

        anchors {
            left: parent.left
            leftMargin: 14
            verticalCenter: parent.top
            verticalCenterOffset: 17
        }
        text: tile.title
        color: Kirigami.Theme.textColor
        font.weight: Font.Bold
        font.pixelSize: Palette.textSize
    }

    Glyph {
        id: leading
        x: 20 - width / 2
        y: 42 - height / 2
        width: 13
        height: 13
        glyph: tile.leadingGlyph
        color: Kirigami.Theme.textColor
    }

    CircleButton {
        id: accessory
        visible: tile.accessoryGlyph.length > 0
        x: tile.width - 14 - width
        y: 42 - height / 2
        width: 28
        height: 28
        bubble: false
        glyph: tile.accessoryGlyph
        toolTip: tile.accessoryToolTip
        glyphScale: 0.62
        onClicked: tile.accessoryClicked()
    }

    Glyph {
        id: trailing
        x: (accessory.visible ? accessory.x - 10 : tile.width - 24 + 8) - width
        y: 42 - height / 2
        width: tile.trailingGlyph.length > 0 ? 16 : 0
        height: 16
        glyph: tile.trailingGlyph
        color: Kirigami.Theme.textColor
    }

    Item {
        id: track

        x: 40
        width: trailing.x - 8 - x
        y: 42 - height / 2
        height: 9

        readonly property real fill: Math.max(0, Math.min(1, tile.value))

        Rectangle {
            anchors.fill: parent
            radius: height / 2
            color: Palette.trackColor(tile.dark)
        }
        Rectangle {
            width: Math.max(parent.height, parent.width * parent.fill)
            visible: parent.fill > 0
            height: parent.height
            radius: height / 2
            color: Palette.fillColor
        }

        MouseArea {
            anchors.fill: parent
            anchors.topMargin: -12
            anchors.bottomMargin: -12
            preventStealing: true

            function update(mouseX: real): void {
                tile.moved(Math.max(0, Math.min(1, mouseX / Math.max(1, track.width))));
            }

            onPressed: mouse => update(mouse.x)
            onPositionChanged: mouse => update(mouse.x)
        }

        WheelHandler {
            onWheel: event => tile.moved(Math.max(0, Math.min(1,
                tile.value + (event.angleDelta.y > 0 ? 0.05 : -0.05))))
        }
    }
}
