/*
    AquaDesktop — the session splash, drawn like the Mac's start-up screen:
    the white Apple logo on black with a thin progress bar under it.
    Every metric is the Plymouth theme's (src/offline/plymouth), so the
    logo and the bar stay on the same pixels from boot to the desktop.

    SPDX-License-Identifier: GPL-3.0-or-later
*/
import QtQuick

Rectangle {
    id: root
    color: "black"

    // Set by ksplashqml: 1 when the session starts, 5 once the desktop
    // is up; the splash closes soon after.
    property int stage

    readonly property int lastStage: 5
    readonly property real logoSize: Math.round(Math.min(width, height) * 0.07)
    readonly property real barWidth: Math.round(width * 0.072)
    readonly property real barHeight: Math.max(4, Math.round(barWidth * 0.02))

    Image {
        id: logo
        anchors.centerIn: parent
        width: root.logoSize
        height: root.logoSize
        source: "images/apple.svg"
        sourceSize.width: width
        sourceSize.height: height
        smooth: true
    }

    // The track: a pill of 20 % white the fill grows along.
    Rectangle {
        id: track
        anchors.horizontalCenter: parent.horizontalCenter
        y: logo.y + logo.height + Math.round(root.height * 0.035)
        width: root.barWidth
        height: root.barHeight
        radius: height / 2
        color: Qt.rgba(1, 1, 1, 0.2)

        Rectangle {
            id: fill
            readonly property real progress: Math.max(0, Math.min(root.stage / root.lastStage, 1))
            height: parent.height
            radius: parent.radius
            color: "white"
            // A pill never narrower than it is tall, like the Mac's.
            width: progress > 0 ? Math.max(height, parent.width * progress) : 0
            Behavior on width {
                NumberAnimation {
                    duration: 600
                    easing.type: Easing.OutCubic
                }
            }
        }
    }
}
