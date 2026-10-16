/*
    AquaDesktop — a Control Center module background: a
    neutral glass bubble, a pill like Wi-Fi and Focus on the macOS Tahoe
    capture (Control.webp); the sliders and Now Playing set their own
    corners.

    SPDX-License-Identifier: GPL-3.0-or-later
*/
import QtQuick

import org.kde.kirigami as Kirigami
import "Palette.js" as Palette

Rectangle {
    id: tile

    property bool hovered: hover.hovered
    readonly property bool dark: Palette.isDark(Kirigami.Theme.textColor)
    // GlassBlur blurs the desktop behind this shape.
    readonly property real glassRadius: radius

    radius: height / 2
    // The glass face (body, lip, speculars) is GlassSurface.
    color: "transparent"

    GlassSurface {
        anchors.fill: parent
        radius: tile.radius
        hovered: tile.hovered
    }

    HoverHandler {
        id: hover
    }
}
