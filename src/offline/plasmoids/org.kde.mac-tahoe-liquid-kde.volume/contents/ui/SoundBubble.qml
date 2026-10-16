/*
    AquaDesktop — the macOS sound bubble as a window's content: one glass
    bubble with 22 px corners around the sound view (VolumeView.qml), with
    transparent room above and below it (Glass rounds a popup like a
    window, which cut the glass's smaller corners when the window ended at
    its edges). KWin blurs behind the glass only. The sound menu and the
    volume HUD both show it.

    SPDX-License-Identifier: GPL-3.0-or-later
*/
import QtQuick

Item {
    id: panel

    // The window is showing: GlassBlur asks again a few times.
    property bool shown: false
    property int glassPad: 28
    property alias interactive: view.interactive
    // The volume HUD's metrics (VolumeView.qml).
    property alias hud: view.hud

    width: bubble.width
    height: bubble.height + 2 * glassPad

    Rectangle {
        id: bubble

        readonly property real glassRadius: radius

        y: panel.glassPad
        width: view.implicitWidth
        height: view.implicitHeight
        radius: 22
        // The Liquid Glass face (GlassSurface.qml); KWin blurs behind it.
        color: "transparent"

        GlassSurface {
            anchors.fill: parent
            z: -1
            radius: bubble.radius
        }

        VolumeView {
            id: view
            anchors.fill: parent
        }
    }

    Loader {
        id: blurLoader
        source: "WindowBlur.qml"
        onLoaded: item.target = panel
    }
    BlurSettler {
        active: panel.shown
        blur: blurLoader.item
    }
}
