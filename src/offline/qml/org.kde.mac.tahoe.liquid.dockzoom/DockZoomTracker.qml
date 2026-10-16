/*
    AquaDesktop — registers a Dock applet with DockZoom.

    Put one at the root of every Dock applet. It marks the applet's resting
    slot (DockZoom watches the cursor for the whole Dock window through a
    DockZoomCatcher it creates once per window) and raises the applet's
    panel container while the cursor is over that slot: magnified icons
    spill over their neighbours' slots, later applets sit on top, and the
    icon under the cursor must be the one that gets drawn and clicked on
    top. It takes no events itself.

    SPDX-License-Identifier: GPL-3.0-or-later
*/
import QtQuick

Item {
    id: tracker

    // Only horizontal Docks magnify; vertical panels keep static icons.
    property bool horizontal: true

    anchors.fill: parent

    property Item container: null
    readonly property Item windowRoot: Window.window ? Window.window.contentItem : null

    function findContainer(): Item {
        for (let item = tracker.parent; item; item = item.parent) {
            if (item.applet !== undefined) {
                return item;
            }
        }
        return null;
    }

    // Keeps the container under its icon while only the Trash widens the
    // Dock (DockZoom.containerShift).
    readonly property Translate containerShift: Translate {
        x: tracker.horizontal && DockZoom.scene !== null && DockZoom.sceneOf(tracker) === DockZoom.scene
           ? DockZoom.containerShift : 0
    }

    function attach(): void {
        if (container && container.transform.length === 1 && container.transform[0] === containerShift) {
            container.transform = [];
        }
        container = findContainer();
        if (container) {
            container.transform = [containerShift];
        }
        if (horizontal && windowRoot) {
            DockZoom.registerTracker(tracker, windowRoot);
        } else {
            DockZoom.unregisterTracker(tracker);
        }
    }

    onParentChanged: Qt.callLater(attach)
    onHorizontalChanged: attach()
    onWindowRootChanged: Qt.callLater(attach)
    Component.onCompleted: Qt.callLater(attach)
    Component.onDestruction: DockZoom.unregisterTracker(tracker)

    Binding {
        target: tracker.container
        property: "z"
        when: tracker.container !== null && tracker.horizontal
        value: DockZoom.stackingFor(tracker)
        restoreMode: Binding.RestoreBindingOrValue
    }
}
