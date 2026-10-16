/*
    AquaDesktop — Wi-Fi, the macOS menu bar item.

    Replaces Plasma's network applet in the menu bar: the same plasma-nm
    backend, shown as the macOS Wi-Fi menu (the switch, the current
    connections, known and other networks, Wi-Fi Settings...).

    Like Now Playing, the menu is a floating dialog of its own, not the
    tray's popup: macOS floats a fully rounded menu a few pixels under the
    menu bar, without the tray's heading.

    SPDX-License-Identifier: GPL-3.0-or-later
*/
import QtQuick
import QtQuick.Layouts

import org.kde.plasma.plasmoid
import org.kde.plasma.core as PlasmaCore
import org.kde.kirigami as Kirigami
import org.kde.plasma.networkmanagement as PlasmaNM

PlasmoidItem {
    id: root

    readonly property int popoverGap: 6
    // Transparent room above and below the glass: the Glass effect rounds
    // this window like a normal one (TopCornerRadius / BottomCornerRadius,
    // 22 px), which cut the glass's own smaller corners when the window
    // ended at its edges. A corner is only cut within that radius of both
    // edges, so vertical room is enough and the width still hugs the screen.
    readonly property int glassPad: 28
    // A click on the icon first deactivates (and so hides) the menu; that
    // same click must not open it again.
    property double popoverHiddenAt: 0

    PlasmaNM.ConnectionIcon {
        id: connectionIcon
    }

    Plasmoid.icon: connectionIcon.connectionIcon
    // No tooltip: macOS shows none on its menu bar extras (and ours would
    // sit over this extra's own menu, which Plasma does not see as open).
    toolTipMainText: ""
    toolTipSubText: ""

    preferredRepresentation: compactRepresentation
    // Plasma's own popup is never used (see the menu below).
    fullRepresentation: Item {}

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

    // Right-aligned under the icon, as macOS opens menu bar menus, kept
    // inside the screen.
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
        popover.y = Math.round(origin.y + anchor.height + popoverGap) - glassPad;
    }

    compactRepresentation: MouseArea {
        id: compact

        hoverEnabled: true
        activeFocusOnTab: true
        onClicked: root.togglePopover()

        Accessible.name: Plasmoid.title
        Accessible.role: Accessible.Button

        Layout.minimumWidth: Kirigami.Units.iconSizes.smallMedium + Kirigami.Units.smallSpacing * 2
        Layout.preferredWidth: Layout.minimumWidth

        // Highlighted only while open, never on hover, like macOS.
        Rectangle {
            anchors.centerIn: parent
            width: Kirigami.Units.iconSizes.smallMedium + Kirigami.Units.smallSpacing * 2
            height: width
            radius: Kirigami.Units.cornerRadius
            color: Qt.rgba(0.5, 0.5, 0.5, 0.25)
            visible: popover.visible
        }

        // Connected to Wi-Fi: the solid macOS fan, 18 px and pure white as in
        // the reference Quickshell menu bar. Other states (wired, offline,
        // connecting) keep the icon theme's glyph.
        readonly property string iconName: connectionIcon.connectionIcon
        readonly property bool wifiConnected: iconName.startsWith("network-wireless")
            && !/disconnected|offline|acquiring|limited|activat/.test(iconName)

        Glyph {
            anchors.centerIn: parent
            visible: compact.wifiConnected
            width: 18
            height: width
            glyph: "wifi"
            color: "white"
        }

        Kirigami.Icon {
            anchors.centerIn: parent
            visible: !compact.wifiConnected
            width: Kirigami.Units.iconSizes.smallMedium
            height: width
            source: compact.iconName
            active: compact.containsMouse
        }
    }

    PlasmaCore.Dialog {
        id: popover

        // No frame from the Plasma theme: one glass panel of our own, as in
        // the reference Quickshell menu bar (shell/shell.qml): 14 px corners,
        // a 1 px rim, 16 px padding, KWin's blur behind it only.
        location: PlasmaCore.Types.Floating
        backgroundHints: PlasmaCore.Dialog.NoBackground
        type: PlasmaCore.Dialog.PopupMenu
        flags: Qt.WindowStaysOnTopHint
        hideOnWindowDeactivate: true
        visible: false
        onVisibleChanged: if (!visible) root.popoverHiddenAt = Date.now()
        onWidthChanged: if (visible) root.placePopover()

        mainItem: Item {
            width: frame.width
            height: frame.height + 2 * root.glassPad

            Rectangle {
                id: frame

                readonly property bool dark: (0.299 * Kirigami.Theme.textColor.r + 0.587 * Kirigami.Theme.textColor.g
                                              + 0.114 * Kirigami.Theme.textColor.b) > 0.5
                readonly property real glassRadius: radius

                y: root.glassPad
                width: view.implicitWidth + 28
                height: view.implicitHeight + 20
                radius: 14
                // The Liquid Glass face (GlassSurface.qml); KWin blurs behind it.
                color: "transparent"

                GlassSurface {
                    anchors.fill: parent
                    z: -1
                    radius: frame.radius
                }

                WifiView {
                    id: view
                    x: 14
                    y: 10
                    width: implicitWidth
                    height: implicitHeight
                    onCloseRequested: popover.visible = false
                }
            }

            Loader {
                id: blurLoader
                source: "WindowBlur.qml"
                onLoaded: item.target = frame.parent
            }
            BlurSettler {
                active: popover.visible
                blur: blurLoader.item
            }
        }
    }
}
