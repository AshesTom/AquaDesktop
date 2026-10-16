/*
    AquaDesktop — Now Playing, the macOS menu bar item.

    A menu bar item, right before the system tray icons, that only shows up
    while an MPRIS player is around, like macOS' play button in the menu
    bar. It replaces the audio badge the Dock no longer draws. It is not a
    tray item on purpose: the tray shows its applets inside its own,
    fixed-width popup with a heading, where macOS shows a small popover.

    The popover is a floating dialog of its own, not Plasma's applet popup:
    on a non-floating panel Plasma glues applet popups to the panel edge
    (square top corners tucked under the bar), where macOS floats a fully
    rounded rectangle a few pixels under the menu bar.

    SPDX-License-Identifier: GPL-3.0-or-later
*/
import QtQuick
import QtQuick.Layouts

import org.kde.plasma.plasmoid
import org.kde.plasma.core as PlasmaCore
import org.kde.kirigami as Kirigami
import org.kde.plasma.private.mpris as Mpris

PlasmoidItem {
    id: root

    readonly property var player: mpris.currentPlayer
    readonly property bool hasPlayer: !!player
    // Gap between the menu bar and the popover, and from the screen edge.
    readonly property int popoverGap: 6
    // A click on the icon first deactivates (and so hides) the popover;
    // that same click must not open it again.
    property double popoverHiddenAt: 0

    Mpris.Mpris2Model {
        id: mpris
    }

    Plasmoid.status: hasPlayer ? PlasmaCore.Types.ActiveStatus : PlasmaCore.Types.HiddenStatus
    Plasmoid.icon: "media-playback-start"
    // No tooltip: macOS shows none on its menu bar extras (and ours would
    // sit over this extra's own menu, which Plasma does not see as open).
    toolTipMainText: ""
    toolTipSubText: ""

    preferredRepresentation: compactRepresentation
    // Plasma's own popup is never used (see the popover below).
    fullRepresentation: Item {}

    onHasPlayerChanged: if (!hasPlayer) popover.visible = false

    Connections {
        target: Plasmoid
        function onActivated(): void {
            root.togglePopover();
        }
    }

    function togglePopover(): void {
        if (popover.visible) {
            popover.visible = false;
            return;
        }
        if (Date.now() - popoverHiddenAt < 300) {
            return;
        }
        placePopover();
        popover.visible = true;
        popover.requestActivate();
    }

    // Centred under the icon, kept inside the screen. Before its first show
    // the dialog has no size yet, so take it from the content and frame.
    function placePopover(): void {
        const anchor = root.compactRepresentationItem;
        if (!anchor) {
            return;
        }
        const origin = anchor.mapToGlobal(0, 0);
        const screen = Plasmoid.containment.screenGeometry;
        const width = popover.width > 0 ? popover.width
            : popover.mainItem.implicitWidth + popover.margins.left + popover.margins.right;
        let x = Math.round(origin.x + anchor.width / 2 - width / 2);
        x = Math.max(screen.x + popoverGap, Math.min(x, screen.x + screen.width - width - popoverGap));
        popover.x = x;
        popover.y = Math.round(origin.y + anchor.height + popoverGap);
    }

    compactRepresentation: MouseArea {
        id: compact

        hoverEnabled: true
        activeFocusOnTab: true
        onClicked: root.togglePopover()

        Accessible.name: Plasmoid.title
        Accessible.role: Accessible.Button

        // Highlighted only while open, never on hover, like macOS.
        Rectangle {
            anchors.centerIn: parent
            width: Kirigami.Units.iconSizes.smallMedium + Kirigami.Units.smallSpacing * 2
            height: width
            radius: Kirigami.Units.cornerRadius
            color: Qt.rgba(0.5, 0.5, 0.5, 0.25)
            visible: popover.visible
        }

        Glyph {
            anchors.centerIn: parent
            width: Kirigami.Units.iconSizes.small
            height: width
            glyph: "play-circle"
        }
    }

    PlasmaCore.Dialog {
        id: popover

        // Floating: the frame draws all four rounded corners.
        location: PlasmaCore.Types.Floating
        type: PlasmaCore.Dialog.PopupMenu
        flags: Qt.WindowStaysOnTopHint
        hideOnWindowDeactivate: true
        visible: false
        onVisibleChanged: if (!visible) root.popoverHiddenAt = Date.now()
        onWidthChanged: if (visible) root.placePopover()

        mainItem: NowPlayingView {
            width: implicitWidth
            height: implicitHeight
            player: root.player
        }
    }
}
