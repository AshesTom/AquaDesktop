/*
    AquaDesktop — the macOS Now Playing menu bar popup.

    Measured on a macOS capture (points): a 298 x 143 popover with 14 pt of
    padding (the Plasma dialog frame provides it), so a 270 x 115 content
    area: 50 pt artwork, title and "Artist – Album" 11 pt to its right, a
    thin progress bar with a vertical playhead at 63.5 pt, the elapsed and
    total times under it, and back / play-pause / forward centred 45 pt
    apart at 96.5 pt.

    This item uses no Plasmoid API, so it can also be rendered on its own.

    SPDX-License-Identifier: GPL-3.0-or-later
*/
import QtQuick

import org.kde.kirigami as Kirigami
import org.kde.plasma.private.mpris as Mpris
import org.kde.ki18n as KI18n

Item {
    // Translations from this widget's catalog in any host: Plasma, or the
    // AquaDesktop shell (Quickshell has no KLocalizedContext).
    KI18n.KI18nContext {
        id: widgetI18n
        translationDomain: "plasma_applet_org.kde.mac-tahoe-liquid-kde.nowplaying"
    }
    function i18nc(context, text, arg1, arg2) {
        if (arg1 === undefined) {
            return widgetI18n.i18nc(context, text);
        }
        return arg2 === undefined ? widgetI18n.i18nc(context, text, arg1)
                                  : widgetI18n.i18nc(context, text, arg1, arg2);
    }
    function i18n(text, arg1) {
        return arg1 === undefined ? widgetI18n.i18n(text) : widgetI18n.i18n(text, arg1);
    }

    id: view

    property var player: null

    readonly property bool hasTrack: !!player && player.track.length > 0
    readonly property bool playing: !!player && player.playbackStatus === Mpris.PlaybackStatus.Playing
    // MPRIS times are in microseconds.
    readonly property real length: player ? player.length : 0
    readonly property real position: player ? player.position : 0
    // Players that publish no length (a paused browser tab, a stream) get
    // no progress row, like macOS; the popover is 26 pt shorter then.
    readonly property bool hasProgress: length > 0

    implicitWidth: 270
    implicitHeight: hasProgress ? 115 : 89

    onVisibleChanged: if (visible && player) player.updatePosition()

    function clock(microseconds: real): string {
        const total = Math.max(0, Math.floor(microseconds / 1000000));
        const hours = Math.floor(total / 3600);
        const minutes = Math.floor((total % 3600) / 60);
        const seconds = total % 60;
        const pad = n => (n < 10 ? "0" : "") + n;
        return hours > 0 ? hours + ":" + pad(minutes) + ":" + pad(seconds)
                         : pad(minutes) + ":" + pad(seconds);
    }

    // MPRIS only signals the position on seeks; poll it while playing.
    Timer {
        interval: 500
        repeat: true
        running: view.visible && view.playing
        onTriggered: view.player.updatePosition()
    }

    Rectangle {
        id: artFrame

        x: 0
        y: 0
        width: 50
        height: 50
        radius: 4
        color: Qt.rgba(Kirigami.Theme.textColor.r, Kirigami.Theme.textColor.g,
                       Kirigami.Theme.textColor.b, 0.10)
        clip: true

        Image {
            id: art
            anchors.fill: parent
            visible: status === Image.Ready
            source: view.player ? view.player.artUrl : ""
            fillMode: Image.PreserveAspectCrop
            asynchronous: true
            sourceSize: Qt.size(100, 100)
        }

        Kirigami.Icon {
            anchors.centerIn: parent
            width: 28
            height: 28
            visible: !art.visible
            source: view.player && view.player.iconName ? view.player.iconName : "media-default-album"
        }
    }

    Column {
        anchors {
            left: artFrame.right
            leftMargin: 11
            right: parent.right
            verticalCenter: artFrame.verticalCenter
        }
        spacing: 1

        Text {
            width: parent.width
            text: view.hasTrack ? view.player.track
                                : (view.player ? view.player.identity : i18nc("@title", "Not Playing"))
            color: Kirigami.Theme.textColor
            font.pixelSize: 15
            font.weight: Font.DemiBold
            elide: Text.ElideRight
        }
        Text {
            width: parent.width
            visible: text.length > 0
            text: {
                if (!view.player) {
                    return "";
                }
                const parts = [view.player.artist, view.player.album].filter(part => part && part.length > 0);
                return parts.join(" – ");
            }
            color: Kirigami.Theme.textColor
            opacity: 0.6
            font.pixelSize: 13
            elide: Text.ElideRight
        }
    }

    // Progress: played part in the text colour, the rest a light track,
    // a 2 x 10 playhead. Click or drag to seek when the player allows it.
    Item {
        id: progress

        readonly property real fraction: view.length > 0 ? Math.min(1, view.position / view.length) : 0

        x: 0
        y: 63.5 - height / 2
        width: parent.width
        height: 10
        visible: view.hasProgress

        Rectangle {
            anchors.verticalCenter: parent.verticalCenter
            width: parent.width
            height: 3
            radius: 1.5
            color: Qt.rgba(Kirigami.Theme.textColor.r, Kirigami.Theme.textColor.g,
                           Kirigami.Theme.textColor.b, 0.18)
        }
        Rectangle {
            anchors.verticalCenter: parent.verticalCenter
            width: Math.round(parent.width * progress.fraction)
            height: 3
            radius: 1.5
            color: Kirigami.Theme.textColor
            opacity: 0.85
        }
        Rectangle {
            x: Math.round(parent.width * progress.fraction - width / 2)
            anchors.verticalCenter: parent.verticalCenter
            width: 2
            height: 10
            radius: 1
            color: Kirigami.Theme.textColor
            visible: view.length > 0
        }
        MouseArea {
            anchors.fill: parent
            anchors.margins: -4
            enabled: !!view.player && view.player.canSeek && view.length > 0
            function seek(x: real): void {
                const target = Math.max(0, Math.min(1, (x - 4) / progress.width)) * view.length;
                view.player.position = target;
            }
            onPressed: mouse => seek(mouse.x)
            onPositionChanged: mouse => { if (pressed) seek(mouse.x); }
        }
    }

    Text {
        x: 0
        y: 69
        visible: view.hasProgress
        text: view.clock(view.position)
        color: Kirigami.Theme.textColor
        opacity: 0.8
        font.pixelSize: 11
        font.features: { "tnum": 1 }
    }
    Text {
        anchors.right: parent.right
        y: 69
        visible: view.hasProgress
        text: view.clock(view.length)
        color: Kirigami.Theme.textColor
        opacity: 0.8
        font.pixelSize: 11
        font.features: { "tnum": 1 }
    }

    Row {
        anchors.horizontalCenter: parent.horizontalCenter
        y: (view.hasProgress ? 96.5 : 70.5) - height / 2
        spacing: 45 - 28

        MediaButton {
            glyph: "previous"
            glyphSize: 23
            enabled: !!view.player && view.player.canGoPrevious
            onClicked: view.player.Previous()
        }
        MediaButton {
            glyph: view.playing ? "pause" : "play"
            glyphSize: 22
            enabled: !!view.player && (view.playing ? view.player.canPause : view.player.canPlay)
            onClicked: view.player.PlayPause()
        }
        MediaButton {
            glyph: "next"
            glyphSize: 23
            enabled: !!view.player && view.player.canGoNext
            onClicked: view.player.Next()
        }
    }

    component MediaButton: Item {
        id: mediaButton

        property alias glyph: icon.glyph
        property int glyphSize: 22
        signal clicked()

        width: 28
        height: 28
        opacity: enabled ? (area.pressed ? 0.45 : 0.75) : 0.3

        Glyph {
            id: icon
            anchors.centerIn: parent
            width: mediaButton.glyphSize
            height: mediaButton.glyphSize
        }
        MouseArea {
            id: area
            anchors.fill: parent
            onClicked: mediaButton.clicked()
        }
    }
}
