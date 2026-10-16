/*
    AquaDesktop — a glass bubble of the clock panel: the Liquid Glass face
    (GlassSurface.qml) with 20 px corners. GlassBlur blurs the desktop
    behind it.

    SPDX-License-Identifier: GPL-3.0-or-later
*/
import QtQuick

import org.kde.kirigami as Kirigami

Rectangle {
    id: card

    readonly property bool dark: (0.299 * Kirigami.Theme.textColor.r + 0.587 * Kirigami.Theme.textColor.g
                                  + 0.114 * Kirigami.Theme.textColor.b) > 0.5
    readonly property real glassRadius: radius
    property bool hovered: false

    radius: Math.min(height / 2, 20)
    color: "transparent"

    GlassSurface {
        anchors.fill: parent
        z: -1
        radius: card.radius
        hovered: card.hovered
    }
}
