/*
    MacTahoe Liquid KDE — one cursor watcher per Dock window.

    Created by DockZoom on top of the whole panel window. Hover inside an
    applet is unreliable for noticing that the cursor left: nothing
    reports a leave when it exits through the floating gap below the
    glass. Watching the whole window, the cursor is tracked across the
    gaps between applets and released the moment it leaves the band the
    Dock widgets cover. The HoverHandler never blocks and the item takes
    no buttons, so everything underneath still gets its events.

    SPDX-License-Identifier: GPL-3.0-or-later
*/
import QtQuick

Item {
    id: catcher

    anchors.fill: parent
    z: 10000000

    HoverHandler {
        blocking: false

        onPointChanged: {
            if (hovered) {
                DockZoom.trackWindowPoint(catcher, point.scenePosition.x, point.scenePosition.y);
            }
        }
        onHoveredChanged: {
            if (!hovered) {
                DockZoom.release();
            }
        }
    }
}
