/*
    AquaDesktop shell — the union of a view's glass shapes, as a Quickshell
    Region: every visible item under `target` declaring `glassRadius >= 0`
    (Tile, CircleButton, the Spotlight panel...), with its corners. The
    popover window blurs behind it (BackgroundEffect.blurRegion) and takes
    clicks only inside it (mask), so the rest stays see-through, like the
    Plasma GlassBlur module does for the plasmoids.

    SPDX-License-Identifier: GPL-3.0-or-later
*/
import QtQuick
import Quickshell

Region {
    id: region

    property Item target: null

    function collect(item: Item, out: var): void {
        if (!item || !item.visible || item.opacity <= 0) {
            return;
        }
        const radius = item.glassRadius;
        if (radius !== undefined && radius >= 0 && item.width > 0 && item.height > 0) {
            out.push({item: item, radius: Math.min(radius, Math.min(item.width, item.height) / 2)});
            return;
        }
        for (const child of item.children) {
            collect(child, out);
        }
    }

    function rebuild(): void {
        for (const old of regions) {
            old.destroy();
        }
        const shapes = [];
        collect(target, shapes);
        const parts = [];
        for (const shape of shapes) {
            parts.push(part.createObject(region, {item: shape.item, radius: shape.radius}));
        }
        regions = parts;
    }

    // Geometry settles over a few frames after a change; rebuild once it has.
    property Timer settle: Timer {
        interval: 16
        onTriggered: region.rebuild()
    }
    function update(): void {
        settle.restart();
    }

    onTargetChanged: update()

    property Connections watcher: Connections {
        target: region.target
        function onWidthChanged(): void { region.update(); }
        function onHeightChanged(): void { region.update(); }
        function onVisibleChanged(): void { region.update(); }
    }

    property Component part: Component {
        Region {}
    }
}
