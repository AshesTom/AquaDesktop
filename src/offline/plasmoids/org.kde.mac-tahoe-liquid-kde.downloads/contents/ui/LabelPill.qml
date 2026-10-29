/*
    MacTahoe Liquid KDE — the black name pill of the macOS Downloads fan:
    25 px tall, white system-font text with 14 px of padding, accent when
    hovered. macOS draws it the same in light and dark mode.

    SPDX-License-Identifier: GPL-3.0-or-later
*/
import QtQuick
import QtQuick.Window
import org.kde.kirigami as Kirigami

Rectangle {
    id: pill

    property alias text: label.text
    property bool highlighted: false
    property real maximumWidth: 1e6
    property int horizontalAlignment: Text.AlignHCenter

    width: Math.min(label.implicitWidth + 28, maximumWidth)
    height: Math.max(25, label.implicitHeight + 8)
    radius: height / 2
    // The fan turns every pill a few degrees. Rotated native text snaps each
    // glyph to the pixel grid on its own, so the letters step up and down;
    // curve-rendered text looks thin and washed out. The pill is therefore
    // drawn upright into a 2x texture, which is then turned smoothly.
    antialiasing: true
    layer.enabled: true
    layer.smooth: true
    layer.textureSize: Qt.size(Math.ceil(width * 2 * Screen.devicePixelRatio),
                               Math.ceil(height * 2 * Screen.devicePixelRatio))
    color: highlighted ? Kirigami.Theme.highlightColor : Qt.rgba(0.04, 0.04, 0.04, 0.92)
    Behavior on color { ColorAnimation { duration: 120 } }

    Text {
        id: label

        anchors {
            fill: parent
            leftMargin: 14
            rightMargin: 14
        }
        color: "white"
        font: Kirigami.Theme.defaultFont
        elide: Text.ElideMiddle
        maximumLineCount: 1
        verticalAlignment: Text.AlignVCenter
        horizontalAlignment: pill.horizontalAlignment
    }
}
