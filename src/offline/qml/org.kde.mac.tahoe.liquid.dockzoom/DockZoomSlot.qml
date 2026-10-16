/*
    AquaDesktop — a Dock widget's slot, magnified as one piece.

    Put the icon AND its MouseArea inside, sized to the widget's resting
    slot. The slot grows from the Dock's bottom edge and moves aside with
    its neighbours, so clicks land where the magnified icon is drawn, not
    where it rests.

    SPDX-License-Identifier: GPL-3.0-or-later
*/
import QtQuick

Item {
    id: slot

    // Only horizontal Docks magnify; vertical panels keep static icons.
    property bool horizontal: true

    readonly property real dockScale: horizontal ? DockZoom.scaleFor(slot) : 1
    // The scale only stretches the resting pixels: while the Dock magnifies,
    // icons inside size themselves `raster` times larger with a 1 / raster
    // scale (top-left origin), so they are rasterized sharp for the zoom.
    readonly property real raster: horizontal && DockZoom.level > 0 ? DockZoom.magnification : 1

    z: dockScale
    transform: [
        Scale {
            origin.x: slot.width / 2
            origin.y: slot.height
            xScale: slot.dockScale
            yScale: slot.dockScale
        },
        Translate {
            x: slot.horizontal ? DockZoom.shiftFor(slot) : 0
        }
    ]
}
