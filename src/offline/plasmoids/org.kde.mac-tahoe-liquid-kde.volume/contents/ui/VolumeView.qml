/*
    AquaDesktop — the macOS sound menu (measured on a macOS Tahoe capture,
    1x): the output's name in bold, then the volume slider between a quiet
    and a loud speaker, on a dotted track. Drawn inside one 322 x 68 px
    glass bubble (SoundBubble.qml).

    The volume HUD (`hud: true`) has its own metrics, measured on a macOS
    Tahoe capture of it (Ars Technica, Retina, halved): 292 x 64, the
    title's centre 18 px down, a 4 px track from 31 px in to 39 px before
    the right edge, centred 41 px down, in white over 10 % white, and its
    17 tick dots 3 px under the track rather than on it.

    No Plasmoid API here, so the view also works outside Plasma.

    SPDX-License-Identifier: GPL-3.0-or-later
*/
import QtQuick

import org.kde.kirigami as Kirigami
import org.kde.plasma.private.volume as PlasmaPa

Item {
    id: view

    readonly property var sink: PlasmaPa.PreferredDevice.sink
    // The volume HUD only shows the level: its slider takes no input.
    property bool interactive: true
    property bool hud: false
    readonly property real level: sink && !sink.muted ? Math.min(1, sink.volume / PlasmaPa.PulseAudio.NormalVolume) : 0

    readonly property int titleY: hud ? 18 : 19
    readonly property int sliderY: hud ? 41 : 45
    readonly property int trackLeft: hud ? 31 : 38
    readonly property int trackRight: hud ? 39 : 42
    readonly property int trackHeight: hud ? 4 : 6
    readonly property color ink: Kirigami.Theme.textColor

    implicitWidth: hud ? 292 : 322
    implicitHeight: hud ? 64 : 68

    function setLevel(value: real): void {
        if (!sink) {
            return;
        }
        value = Math.max(0, Math.min(1, value));
        sink.volume = Math.round(value * PlasmaPa.PulseAudio.NormalVolume);
        sink.muted = value <= 0;
    }

    Text {
        x: 17
        y: view.titleY - height / 2
        width: parent.width - 34
        text: view.sink ? (view.sink.description || view.sink.name) : ""
        color: Kirigami.Theme.textColor
        font.pixelSize: 13
        font.weight: Font.Bold
        elide: Text.ElideRight
    }

    Glyph {
        x: 16
        y: view.sliderY - height / 2
        width: 16
        height: 16
        glyph: "speaker-0"
    }
    Glyph {
        x: parent.width - 16 - width
        y: view.sliderY - height / 2
        width: 20
        height: 20
        glyph: "speaker-3"
    }

    // The track: 17 dots along it (under it in the HUD), the level in white.
    Item {
        id: track
        x: view.trackLeft
        width: parent.width - view.trackLeft - view.trackRight
        y: view.sliderY - height / 2
        height: view.trackHeight

        Rectangle {
            anchors.fill: parent
            radius: height / 2
            color: Qt.rgba(view.ink.r, view.ink.g, view.ink.b, view.hud ? 0.10 : 0.18)
        }
        Repeater {
            model: 17
            delegate: Rectangle {
                required property int index
                x: view.hud ? 4 + index * (track.width - 9) / 16 : 3 + index * (track.width - 8) / 16
                y: view.hud ? track.height + 3 : (track.height - height) / 2
                width: 2
                height: 2
                radius: 1
                color: Qt.rgba(view.ink.r, view.ink.g, view.ink.b, view.hud ? 0.40 : 0.45)
            }
        }
        Rectangle {
            width: Math.max(height, track.width * view.level)
            visible: view.level > 0
            height: parent.height
            radius: height / 2
            color: view.hud ? "#ffffff" : "#f2f2f4"
        }
        MouseArea {
            anchors.fill: parent
            anchors.margins: -10
            enabled: view.interactive
            onPressed: mouse => view.setLevel((mouse.x - 10) / track.width)
            onPositionChanged: mouse => {
                if (pressed) {
                    view.setLevel((mouse.x - 10) / track.width);
                }
            }
        }
    }
}
