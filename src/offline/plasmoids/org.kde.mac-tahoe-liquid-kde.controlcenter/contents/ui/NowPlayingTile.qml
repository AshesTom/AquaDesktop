/*
    AquaDesktop — Control Center Now Playing module (MPRIS).

    SPDX-License-Identifier: GPL-3.0-or-later
*/
import QtQuick
import QtQuick.Layouts

import org.kde.kirigami as Kirigami
import "Palette.js" as Palette
import org.kde.plasma.private.mpris as Mpris
import org.kde.ki18n as KI18n

Tile {
    // Rounded corners follow the 140 px square tile in the supplied capture.
    radius: 28

    // Translations from this widget's catalog in any host: Plasma, or the
    // AquaDesktop shell (Quickshell has no KLocalizedContext).
    KI18n.KI18nContext {
        id: widgetI18n
        translationDomain: "plasma_applet_org.kde.mac-tahoe-liquid-kde.controlcenter"
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

    id: tile

    readonly property var player: mpris.currentPlayer
    readonly property bool hasTrack: !!player && player.track.length > 0
    readonly property bool playing: !!player && player.playbackStatus === Mpris.PlaybackStatus.Playing

    implicitWidth: 140
    implicitHeight: 140

    Mpris.Mpris2Model {
        id: mpris
    }

    Image {
        id: art

        anchors {
            left: parent.left
            top: parent.top
            margins: 12
        }
        // macOS Tahoe: 52 px artwork, 16 px in.
        width: 48
        height: 48
        visible: tile.hasTrack && status === Image.Ready
        source: tile.player ? tile.player.artUrl : ""
        fillMode: Image.PreserveAspectCrop
        asynchronous: true
        sourceSize: Qt.size(96, 96)
        layer.enabled: true
    }

    // macOS keeps the artwork square even with nothing playing.
    Rectangle {
        anchors.fill: art
        radius: 8
        color: Palette.innerDisc(Palette.isDark(Kirigami.Theme.textColor), false)
        visible: !art.visible
    }

    Kirigami.Icon {
        anchors.fill: art
        visible: tile.hasTrack && !art.visible
        source: tile.player ? tile.player.iconName : ""
    }

    ColumnLayout {
        anchors {
            left: parent.left
            right: parent.right
            margins: 12
            top: art.bottom
            topMargin: 12
        }
        spacing: 0

        Text {
            Layout.fillWidth: true
            text: tile.hasTrack ? tile.player.track : i18nc("@title Control Center module", "Not Playing")
            color: Kirigami.Theme.textColor
            font.weight: Font.Bold
            font.pixelSize: Palette.textSize
            elide: Text.ElideRight
            horizontalAlignment: Text.AlignLeft
        }
        Text {
            Layout.fillWidth: true
            visible: tile.hasTrack && text.length > 0
            text: tile.player ? tile.player.artist : ""
            color: Kirigami.Theme.textColor
            opacity: 0.6
            font.pixelSize: Palette.textSize - 1
            elide: Text.ElideRight
        }
    }

    RowLayout {
        anchors {
            horizontalCenter: parent.horizontalCenter
            bottom: parent.bottom
            // Centred 19 px above the bottom edge, 45 px apart.
            bottomMargin: 19 - height / 2
        }
        spacing: 45 - 28
        opacity: tile.player ? 1 : 0.5

        MediaButton {
            glyph: "previous"
            size: 18
            enabled: !!tile.player && tile.player.canGoPrevious
            onClicked: tile.player.Previous()
        }
        MediaButton {
            glyph: tile.playing ? "pause" : "play"
            size: 17
            enabled: !!tile.player && (tile.playing ? tile.player.canPause : tile.player.canPlay)
            onClicked: tile.player.PlayPause()
        }
        MediaButton {
            glyph: "next"
            size: 18
            enabled: !!tile.player && tile.player.canGoNext
            onClicked: tile.player.Next()
        }
    }

    component MediaButton: Item {
        id: mediaButton

        property alias glyph: icon.glyph
        property int size: 18
        signal clicked()

        implicitWidth: 28
        implicitHeight: 28
        opacity: enabled ? (area.pressed ? 0.5 : 1) : 0.4

        Glyph {
            id: icon
            anchors.centerIn: parent
            width: mediaButton.size
            height: mediaButton.size
        }
        MouseArea {
            id: area
            anchors.fill: parent
            onClicked: mediaButton.clicked()
        }
    }
}
