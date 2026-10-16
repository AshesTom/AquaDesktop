/*
    AquaDesktop — shared Dock magnification state.

    Every Dock widget (Launcher, task manager, Downloads stack, minimized
    windows, Trash, separators) is its own applet, but they all live in the
    same plasmashell QML engine, so this singleton is shared between them.
    DockZoomTracker feeds it the cursor position; each Dock item asks it for
    its own scale and sideways shift. That is what makes the magnification
    parabolic across the whole Dock instead of per applet.

    The scale follows a cosine bell centred on the cursor. The shift is the
    integral of the extra width of that bell, so neighbours move apart by
    exactly the space the magnified icons need. The glass widens to hold
    them: the first and last Dock widgets (Launcher and Trash) register as
    growth owners and widen on their outer side. Plasma resizes and
    re-centres a "fit" panel in two separate steps, so a glass that
    followed the cursor resized the Dock on every move and made it shake.
    The glass therefore only depends on `level`: it widens symmetrically
    by the bell's largest outward spread while the magnification eases in,
    stays put while the cursor moves, and narrows smoothly as it eases out. Every applet
    container moves with its icon (DockZoomTracker, containerShift), which keeps clicks on the icon drawn
    under the cursor. Positions are computed in the resting frame (as if
    the Dock had not grown), so the resize never feeds back into the
    cursor maths.

    Everything scales with `level`, which eases in when the cursor enters
    the Dock and out when it leaves. The theme's panel-background reserves
    the headroom above the Dock glass (floating-hint-top-margin), so the
    magnified icons are not clipped.

    SPDX-License-Identifier: GPL-3.0-or-later
*/
pragma Singleton

import QtQuick

QtObject {
    id: zoom

    // Peak scale of the icon under the cursor (1.0 disables magnification).
    // The task manager binds it to its "Hover magnification" setting.
    property real magnification: 1.6
    // Half-width of the bell, in Dock thicknesses (~2.6 icons each side).
    property real reach: 2.0
    // Gap between the Dock window edge and its glass on the left/right
    // (floating-hint-left/right-margin in widgets/panel-background).
    property real sideRoom: 8

    // Live state, written by DockZoomTracker.
    property Item scene: null
    property real thickness: 0
    property real level: 0

    // Widgets able to widen the Dock: {item, base, leading}. One leading
    // (Launcher) and one trailing (Trash) owner per Dock, i.e. per screen.
    property var growthOwners: []
    property Item leadOwner: null
    property real leadBase: 0
    property Item trailOwner: null
    property real trailBase: 0
    property real restRight: 0

    readonly property real radius: Math.max(1, reach * thickness)
    readonly property real amplitude: Math.max(0, magnification - 1) * level

    // Extra width currently laid out by each owner.
    readonly property real appliedLead: leadOwner ? Math.max(0, leadOwner.width - leadBase) : 0
    readonly property real appliedTrail: trailOwner ? Math.max(0, trailOwner.width - trailBase) : 0
    // Window x minus resting-frame x. The leading growth pushes every
    // applet right inside the window; without a leading owner the window
    // grows around its centre by the trailing growth alone.
    readonly property real frameOffset: leadOwner ? appliedLead : appliedTrail / 2
    // Without a leading owner (the Launcher hidden behind the "Apps" pin),
    // re-centring the grown panel slides every applet container left by
    // half the trailing growth. DockZoomTracker moves each container back
    // by this much, so containers stay under their icons: Qt delivers no
    // input to the parts of an icon drawn outside its applet container
    // (the Downloads stack was unclickable while the Dock magnified).
    readonly property real containerShift: !leadOwner && trailOwner ? appliedTrail / 2 : 0

    // Cursor in the resting frame, captured per hover event against the
    // geometry that event saw.
    property real cursorRest: 0

    // The bell's largest outward spread on each side, at full magnification.
    readonly property real fullSpread: Math.max(0, magnification - 1) * radius / 2

    Behavior on level {
        NumberAnimation {
            duration: 180
            easing.type: Easing.OutCubic
        }
    }

    // A short grace period so a single stray hover event never collapses
    // the Dock mid-gesture.
    property Timer releaseTimer: Timer {
        interval: 40
        onTriggered: zoom.level = 0
    }

    // Registered DockZoomTrackers (one per Dock applet) and one
    // DockZoomCatcher per Dock window, keyed by nothing but its scene.
    property var trackers: []
    property var catchers: []
    readonly property Component catcherComponent: Qt.createComponent("DockZoomCatcher.qml")

    function registerTracker(tracker: Item, root: Item): void {
        if (trackers.indexOf(tracker) < 0) {
            trackers = trackers.concat([tracker]);
        }
        catchers = catchers.filter(catcher => catcher && catcher.parent);
        if (!catchers.some(catcher => catcher.parent === root)) {
            const catcher = catcherComponent.createObject(root);
            if (catcher) {
                catchers = catchers.concat([catcher]);
            }
        }
    }

    function unregisterTracker(tracker: Item): void {
        trackers = trackers.filter(entry => entry !== tracker);
    }

    // Window-wide cursor position from a DockZoomCatcher: track while it
    // is over the band the Dock widgets cover, release anywhere else.
    function trackWindowPoint(catcher: Item, sceneX: real, sceneY: real): void {
        const root = catcher.parent;
        let inside = null;
        let left = Infinity, right = -Infinity, top = Infinity, bottom = -Infinity;
        for (const tracker of trackers) {
            if (!tracker || sceneOf(tracker) !== root || !tracker.visible) {
                continue;
            }
            const origin = tracker.mapToItem(null, 0, 0);
            left = Math.min(left, origin.x);
            right = Math.max(right, origin.x + tracker.width);
            top = Math.min(top, origin.y);
            bottom = Math.max(bottom, origin.y + tracker.height);
            inside = inside || tracker;
        }
        if (inside && sceneX >= left && sceneX < right && sceneY >= top && sceneY < bottom) {
            track(inside, sceneX, bottom - top);
        } else {
            release();
        }
    }

    function sceneOf(item: Item): Item {
        let root = item;
        while (root && root.parent) {
            root = root.parent;
        }
        return root;
    }

    function registerGrowthOwner(item: Item, baseWidth: real, leading: bool): void {
        unregisterGrowthOwner(item);
        growthOwners = growthOwners.concat([{ item: item, base: baseWidth, leading: !!leading }]);
    }

    function unregisterGrowthOwner(item: Item): void {
        growthOwners = growthOwners.filter(entry => entry.item !== item);
        if (leadOwner === item) {
            leadOwner = null;
        }
        if (trailOwner === item) {
            trailOwner = null;
        }
    }

    function track(item: Item, sceneX: real, dockThickness: real): void {
        releaseTimer.stop();
        const newScene = sceneOf(item);
        if (newScene !== scene) {
            scene = newScene;
            level = 0;
        }
        const lead = growthOwners.find(entry => entry.leading && sceneOf(entry.item) === scene);
        const trail = growthOwners.find(entry => !entry.leading && sceneOf(entry.item) === scene);
        leadBase = lead ? lead.base : 0;
        leadOwner = lead ? lead.item : null;
        trailBase = trail ? trail.base : 0;
        trailOwner = trail ? trail.item : null;
        if (trail) {
            // The trailing owner grows on its outer side, so its leading
            // edge only moves with the leading growth.
            restRight = trail.item.mapToItem(null, trail.base, 0).x - containerShift
                - (leadOwner ? appliedLead : 0);
        }
        thickness = dockThickness;
        cursorRest = sceneX - frameOffset;
        if (magnification > 1) {
            level = 1;
        }
    }

    function release(): void {
        releaseTimer.restart();
    }

    // Extra width of the bell between the cursor and `delta` px away from it.
    function integral(delta: real): real {
        const clamped = Math.max(-radius, Math.min(radius, delta));
        return amplitude / 2
            * (clamped + radius / Math.PI * Math.sin(Math.PI * clamped / radius));
    }

    // Signed distance from the cursor to the item's resting centre. Uses the
    // untransformed parent so the item's own zoom transform never feeds back.
    function deltaFor(item: Item): real {
        if (!item || !item.parent || amplitude <= 0 || sceneOf(item) !== scene) {
            return NaN;
        }
        const centre = item.parent.mapToItem(null, item.x + item.width / 2, 0).x;
        return centre - containerShift - (leadOwner ? appliedLead : 0) - cursorRest;
    }

    function scaleFor(item: Item): real {
        const delta = deltaFor(item);
        if (isNaN(delta) || Math.abs(delta) >= radius) {
            return 1;
        }
        return 1 + amplitude * (1 + Math.cos(Math.PI * delta / radius)) / 2;
    }

    function shiftFor(item: Item): real {
        const delta = deltaFor(item);
        if (isNaN(delta)) {
            return 0;
        }
        if (!trailOwner && !leadOwner) {
            // Without a widget to widen the glass, stay inside the window.
            return Math.max(-sideRoom, Math.min(sideRoom, integral(delta)));
        }
        // Both ends grow: re-centring the panel already slides the Dock.
        // Only the end grows: the containers slide back (containerShift).
        return integral(delta);
    }

    // Stacking order for the applet whose resting slot is `tracker`: the
    // closer it is to the cursor, the higher. Always within (0, 1].
    function stackingFor(tracker: Item): real {
        if (level <= 0 || sceneOf(tracker) !== scene) {
            return 0;
        }
        // Resting slot of the tracker's applet: owners only count their
        // base width, without the growth on their outer side.
        let left = tracker.mapToItem(null, 0, 0).x - containerShift - (leadOwner ? appliedLead : 0);
        let width = tracker.width;
        if (tracker.parent === leadOwner) {
            left += appliedLead;
            width = leadBase;
        } else if (tracker.parent === trailOwner) {
            width = trailBase;
        }
        const distance = Math.max(0, left - cursorRest, cursorRest - left - width);
        return 1 / (1 + distance);
    }

    // Extra width the growth owner `item` should lay out right now.
    // Each side grows in even steps: the "fit" panel re-centres on every
    // resize, and an odd total width puts that centre on a half pixel, so
    // the whole Dock would shake by 1 px from frame to frame while it
    // grows and shrinks.
    function evenStep(value: real): int {
        return 2 * Math.round(value / 2);
    }

    // Follows only `level`, never the cursor: the panel is resized while
    // the magnification eases in and out, not while the cursor moves.
    function growthFor(item: Item): real {
        const spread = fullSpread * level;
        if (spread <= 0) {
            return 0;
        }
        if (item === leadOwner) {
            return evenStep(spread);
        }
        if (item === trailOwner) {
            return evenStep(leadOwner ? spread : 2 * spread);
        }
        return 0;
    }
}
