/*
    SPDX-FileCopyrightText: 2024 Kelvin Fonseca
    SPDX-License-Identifier: GPL-2.0-or-later

    Minimized-window thumbnail for the Dock's minimized-windows section,
    derived from the macesque task manager's TaskImage
    (https://github.com/snpynk/macesque-taskmanager).

    Grabs a single frame of the window's PipeWire screencast, then drops the
    stream and keeps the frozen image, so a Dock full of minimized windows
    costs nothing while idle. The app icon sits in the bottom-right corner,
    like macOS. Without screencasting (X11), `ready` stays false and the
    delegate keeps showing the plain app icon.
*/

import QtQuick

import org.kde.kirigami as Kirigami
import org.kde.pipewire as PipeWire
import org.kde.taskmanager as TaskManager

Item {
    id: thumbnail

    property var winId
    property var appIcon

    // The grab result must stay alive for its URL to remain valid.
    property var grab: null
    readonly property bool ready: frozen.status === Image.Ready

    onWinIdChanged: grab = null

    Loader {
        anchors.fill: parent
        opacity: 0
        asynchronous: true
        active: thumbnail.winId !== undefined && thumbnail.grab === null

        sourceComponent: PipeWire.PipeWireSourceItem {
            id: source

            nodeId: request.nodeId

            TaskManager.ScreencastingRequest {
                id: request
                uuid: thumbnail.winId
            }

            onReadyChanged: {
                if (ready) {
                    source.grabToImage(result => {
                        thumbnail.grab = result;
                    });
                }
            }
        }
    }

    Image {
        id: frozen

        anchors.fill: parent
        source: thumbnail.grab ? thumbnail.grab.url : ""
        fillMode: Image.PreserveAspectFit
        asynchronous: true
        smooth: true
        mipmap: true
    }

    Kirigami.Icon {
        visible: thumbnail.ready
        anchors {
            right: parent.right
            bottom: parent.bottom
        }
        width: Math.round(parent.width * 0.42)
        height: width
        roundToIconSize: false
        source: thumbnail.appIcon
    }
}
