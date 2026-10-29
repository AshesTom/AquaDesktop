/*
    MacTahoe Liquid KDE — Control Center.

    The two-toggle glyph of the macOS menu bar, opening the Tahoe Control
    Center: Wi-Fi, Bluetooth, AirDrop, Now Playing, Focus, Stage Manager,
    Screen Mirroring, Display, Sound, Dark Mode, Calculator, Timer and
    Screenshot (see ControlCenterView).

    SPDX-License-Identifier: GPL-3.0-or-later
*/
import QtQuick
import QtQuick.Layouts

import org.kde.plasma.plasmoid
import org.kde.plasma.core as PlasmaCore
import org.kde.plasma.plasma5support as P5Support
import org.kde.kirigami as Kirigami

PlasmoidItem {
    id: root

    Plasmoid.backgroundHints: PlasmaCore.Types.NoBackground

    // The tray toggles its menu on activation.
    Timer {
        id: trayOpener
        interval: 200
        onTriggered: if (root.trayApplet) root.trayApplet.activated()
    }

    // The menu bar's system tray (ours, or Plasma's), whose menu the
    // "Other Status Items" bubble opens.
    readonly property var trayApplet: {
        const applets = Plasmoid.containment ? Plasmoid.containment.applets : [];
        for (const applet of applets) {
            if (applet.pluginName === "org.kde.mac.tahoe.liquid.systemtray"
                || applet.pluginName === "org.kde.plasma.systemtray") {
                return applet;
            }
        }
        return null;
    }
    Plasmoid.icon: "configure"
    Plasmoid.title: i18n("Control Center")
    // No tooltip: macOS shows none on its menu bar extras (and ours would
    // sit over this extra's own menu, which Plasma does not see as open).
    toolTipMainText: ""
    toolTipSubText: ""

    preferredRepresentation: compactRepresentation
    // Always a popup, never inlined in the panel.
    switchWidth: Infinity
    switchHeight: Infinity

    P5Support.DataSource {
        id: executable

        engine: "executable"
        connectedSources: []
        onNewData: (sourceName, data) => disconnectSource(sourceName)
    }

    function run(command: string): void {
        executable.connectSource(command);
    }

    // The popover is a floating dialog of its own, not Plasma's applet popup:
    // on a non-floating panel Plasma glues applet popups to the panel edge
    // (square top corners tucked under the bar), where macOS floats a fully
    // rounded rectangle a few pixels under the menu bar.
    readonly property int popoverGap: 6
    // Transparent room above and below the glass: the Glass effect rounds
    // this window like a normal one (TopCornerRadius / BottomCornerRadius,
    // 22 px), which cut the glass's own smaller corners when the window
    // ended at its edges. A corner is only cut within that radius of both
    // edges, so vertical room is enough and the width still hugs the screen.
    readonly property int glassPad: 28
    // A click on the icon first deactivates (and so hides) the popover;
    // that same click must not open it again.
    property double popoverHiddenAt: 0

    // Plasma's own popup is never used.
    fullRepresentation: Item {}

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
        popover.y = Math.round(origin.y + anchor.height + popoverGap) - glassPad;
    }

    Connections {
        target: Plasmoid
        function onActivated(): void {
            root.togglePopover();
        }
    }

    compactRepresentation: MouseArea {
        id: button

        readonly property bool vertical: Plasmoid.formFactor === PlasmaCore.Types.Vertical
        // A 36 px pitch with the panel's applet spacing, like the macOS menu
        // bar extras (1x Tahoe capture).
        readonly property int pitch: Kirigami.Units.iconSizes.smallMedium + Kirigami.Units.largeSpacing
            + Kirigami.Units.smallSpacing / 2

        Layout.minimumWidth: vertical ? -1 : pitch
        Layout.maximumWidth: vertical ? -1 : pitch
        Layout.minimumHeight: vertical ? pitch : -1
        Layout.maximumHeight: vertical ? pitch : -1
        Layout.fillHeight: !vertical
        Layout.fillWidth: vertical

        hoverEnabled: true
        activeFocusOnTab: true
        onClicked: root.togglePopover()

        Accessible.name: Plasmoid.title
        Accessible.role: Accessible.Button

        // Like a macOS menu bar extra: highlighted only while open, never on
        // hover (the system tray behaves the same).
        Rectangle {
            anchors.centerIn: parent
            width: Kirigami.Units.iconSizes.smallMedium + Kirigami.Units.smallSpacing * 2
            height: width
            radius: Kirigami.Units.cornerRadius
            color: Qt.rgba(0.5, 0.5, 0.5, 0.25)
            visible: popover.visible
        }

        // 18 px and pure white, as in the reference Quickshell menu bar
        // (the panel's text colour is a grey #dedede).
        Glyph {
            anchors.centerIn: parent
            width: 18
            height: width
            glyph: "controlcenter"
            color: "white"
        }
    }

    PlasmaCore.Dialog {
        id: popover

        // Floating under the menu bar, with no frame of its own: the
        // modules are separate glass bubbles, like Golden Gate.
        location: PlasmaCore.Types.Floating
        backgroundHints: PlasmaCore.Dialog.NoBackground
        type: PlasmaCore.Dialog.PopupMenu
        flags: Qt.WindowStaysOnTopHint
        hideOnWindowDeactivate: true
        visible: false
        onVisibleChanged: if (!visible) root.popoverHiddenAt = Date.now()
        onWidthChanged: if (visible) root.placePopover()

        // Fixed size, like every macOS menu bar extra.
        mainItem: Item {
            // With no frame the modules would touch the menu bar: Golden
            // Gate leaves 14 px between the bar and the first row.
            readonly property int topInset: 8

            width: view.implicitWidth
            height: view.implicitHeight + topInset + 2 * root.glassPad

            ControlCenterView {
                id: view

                y: parent.topInset + root.glassPad

                width: implicitWidth
                height: implicitHeight
                onRunCommand: command => root.run(command)
                onCloseRequested: popover.visible = false
                onEditControlsRequested: {
                    popover.visible = false;
                    Plasmoid.internalAction("configure").trigger();
                }
                showStatusItems: root.trayApplet !== null
                onStatusItemsRequested: {
                    popover.visible = false;
                    // Once this popover is gone: closing it deactivates the
                    // tray's menu too, if it opened first.
                    trayOpener.restart();
                }
            }

            // KWin blurs the desktop behind each module, not behind the
            // whole popover (see WindowBlur.qml).
            Loader {
                id: blurLoader
                source: "WindowBlur.qml"
                onLoaded: item.target = view
            }
            BlurSettler {
                active: popover.visible
                blur: blurLoader.item
            }
        }
    }
}
