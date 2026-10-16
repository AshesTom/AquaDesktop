/*
    AquaDesktop shell — a menu bar popover (Control Center, Wi-Fi, Spotlight):
    a borderless layer surface floating under the menu bar, the desktop
    blurred behind its glass shapes only (GlassRegion), clicks taken only on
    them. It never resizes while open: `content` lays itself out inside.

    SPDX-License-Identifier: GPL-3.0-or-later
*/
import QtQuick
import Quickshell
import Quickshell.Wayland

PanelWindow {
    id: popover

    // The view shown; its glass shapes declare `glassRadius`.
    default property alias content: holder.data
    property Item view: null
    // Left edge, in screen coordinates.
    property int popoverX: 0
    property int popoverY: 36
    // Spotlight takes the keyboard; the others only when clicked.
    property bool takesKeyboard: false
    // Transparent room around the view: the Glass effect rounds a dock
    // surface's blur with DockCornerRadius (24 px), which would cut the
    // view's own, smaller corners if the window ended at its edges.
    readonly property int pad: 28
    readonly property int padLeft: Math.min(pad, popoverX)
    readonly property int padTop: Math.min(pad, popoverY)
    readonly property int viewWidth: view ? Math.max(1, view.width) : 1
    readonly property int viewHeight: view ? Math.max(1, view.height) : 1
    // Kept on screen: a layer surface wider than its room gets moved.
    readonly property int padRight: screen ? Math.max(0, Math.min(pad, screen.width - popoverX - viewWidth)) : 0
    readonly property int padBottom: screen ? Math.max(0, Math.min(pad, screen.height - popoverY - viewHeight)) : 0

    signal dismissed()

    function open(): void {
        visible = true;
        glass.update();
    }
    // The glass shapes moved without the view resizing (Spotlight's panel).
    function refreshGlass(): void {
        glass.update();
    }
    function close(): void {
        if (visible) {
            visible = false;
            dismissed();
        }
    }

    visible: false
    color: "transparent"
    anchors {
        top: true
        left: true
    }
    margins {
        top: popoverY - padTop
        left: popoverX - padLeft
    }
    implicitWidth: padLeft + viewWidth + padRight
    implicitHeight: padTop + viewHeight + padBottom
    exclusionMode: ExclusionMode.Ignore

    WlrLayershell.layer: WlrLayer.Overlay
    // "dock": the Glass effect never force-blurs dock surfaces, so only
    // the glass shapes get blurred.
    WlrLayershell.namespace: "dock"
    WlrLayershell.keyboardFocus: takesKeyboard ? WlrKeyboardFocus.Exclusive : WlrKeyboardFocus.OnDemand

    BackgroundEffect.blurRegion: glass
    mask: glass

    GlassRegion {
        id: glass
        target: popover.view
    }

    Item {
        id: holder
        anchors.fill: parent
        anchors.leftMargin: popover.padLeft
        anchors.topMargin: popover.padTop
        anchors.rightMargin: popover.padRight
        anchors.bottomMargin: popover.padBottom
        Keys.onEscapePressed: popover.close()
    }
}
