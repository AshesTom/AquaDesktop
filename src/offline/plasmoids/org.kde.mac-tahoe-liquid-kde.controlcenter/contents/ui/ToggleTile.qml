/*
    MacTahoe Liquid KDE — two-cell Control Center toggle (Wi-Fi, Focus):
    a round toggle followed by a title and its state. The round part
    toggles; the text part opens the details.

    SPDX-License-Identifier: GPL-3.0-or-later
*/
import QtQuick
import QtQuick.Layouts

import org.kde.kirigami as Kirigami
import "Palette.js" as Palette

Tile {
    id: tile

    property string glyph
    property string title
    property string subtitle
    property bool wrapTitle: false
    property bool active: false
    property color activeColor: Kirigami.Theme.highlightColor

    signal toggled()
    signal detailsRequested()

    implicitWidth: 140
    implicitHeight: 64
    opacity: enabled ? 1 : 0.5

    CircleButton {
        id: toggle

        anchors {
            left: parent.left
            // Tahoe uses a 36 px disc, inset 14 px in a 64 px tile.
            leftMargin: (parent.height - width) / 2
            verticalCenter: parent.verticalCenter
        }
        width: 36
        height: width
        bubble: false
        glyph: tile.glyph
        active: tile.active
        activeColor: tile.activeColor
        toolTip: tile.title
        glyphScale: 0.56
        onClicked: tile.toggled()
    }

    // Keep the title and state aligned within the compact tile.
    ColumnLayout {
        id: labels
        anchors {
            left: toggle.right
            leftMargin: 8
            right: parent.right
            rightMargin: 10
            top: parent.top
            topMargin: tile.wrapTitle ? Math.max(2, (parent.height - implicitHeight) / 2)
                                     : 28 - titleLabel.implicitHeight / 2
        }
        spacing: 2

        Text {
            id: titleLabel
            Layout.fillWidth: true
            text: tile.title
            color: Kirigami.Theme.textColor
            font.weight: Font.Bold
            font.pixelSize: Palette.textSize
            maximumLineCount: tile.wrapTitle ? 2 : 1
            wrapMode: tile.wrapTitle ? Text.WordWrap : Text.NoWrap
            elide: tile.wrapTitle ? Text.ElideNone : Text.ElideRight
        }
        Text {
            Layout.fillWidth: true
            visible: text.length > 0
            text: tile.subtitle
            color: Kirigami.Theme.textColor
            opacity: 0.65
            font.pixelSize: Palette.smallTextSize
            maximumLineCount: 1
            elide: Text.ElideRight
        }
    }

    MouseArea {
        anchors {
            left: toggle.right
            right: parent.right
            top: parent.top
            bottom: parent.bottom
        }
        onClicked: tile.detailsRequested()
    }
}
