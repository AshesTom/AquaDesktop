/*
    AquaDesktop — one glass bubble of the notification history: the Liquid
    Glass face (GlassSurface.qml, the menu bar popovers' copy) with 24 px
    corners and no drawn border. `glassRadius` publishes the bubble to
    GlassBlur, so KWin blurs the desktop behind each card on its own (and
    Better Blur DX's liquid style draws one lens per card).

    SPDX-License-Identifier: GPL-3.0-or-later
*/
import QtQuick

Item {
    id: card

    property real radius: 24
    property bool hovered: false
    readonly property real glassRadius: radius

    GlassSurface {
        anchors.fill: parent
        z: -1
        radius: Math.min(card.radius, card.width / 2, card.height / 2)
        hovered: card.hovered
    }
}
