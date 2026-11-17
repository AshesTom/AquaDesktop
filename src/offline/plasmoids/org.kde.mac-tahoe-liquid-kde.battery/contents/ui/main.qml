/*
    MacTahoe Liquid KDE — Battery, the macOS menu bar item: "72%" beside the battery
    glyph (BatteryGlyph.qml), a bolt while charging, and the macOS Battery
    menu on click. Replaces Plasma's battery applet in the menu bar; that
    applet stays hidden in the tray. Gone on machines without a battery.

    The charge comes from Plasma's powermanagement data engine; the apps
    using significant energy from their CPU time per systemd app unit
    (code/significant-energy.sh), sampled while the menu is open.

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

    readonly property var battery: pmSource.data["Battery"] || {}
    readonly property bool hasBattery: battery["Has Battery"] === true
    readonly property real percent: battery["Percent"] || 0
    readonly property bool pluggedIn: (pmSource.data["AC Adapter"] || {})["Plugged in"] === true
    readonly property bool charging: battery["State"] === "Charging"
    readonly property real remainingMs: battery["Remaining msec"] || 0

    property int chargeLimit: 0
    // Read hardware charge limits only. No writes, no daemon assumptions.
    // Show a limit only when reported thresholds agree across batteries.
    readonly property string chargeLimitCommand: "for b in /sys/class/power_supply/*; do "
        + "[ \"$(cat \"$b/type\" 2>/dev/null)\" = Battery ] || continue; "
        + "cat \"$b/charge_control_end_threshold\" 2>/dev/null; done"

    property var energyApplications: null
    // An app is significant from 20% of one core, averaged over the sample.
    readonly property string energyCommand: "sh '"
        + decodeURIComponent(Qt.resolvedUrl("../code/significant-energy.sh").toString().replace(/^file:\/\//, ""))
        + "' 20"

    readonly property int popoverGap: 6
    // Transparent room above and below the glass (see the Wi-Fi menu):
    // the Glass effect rounds this window like a normal one.
    readonly property int glassPad: 28
    property double popoverHiddenAt: 0

    Plasmoid.status: hasBattery ? PlasmaCore.Types.ActiveStatus : PlasmaCore.Types.HiddenStatus
    Plasmoid.icon: "battery-full"
    // No tooltip: macOS shows none on its menu bar extras (and ours would
    // sit over this extra's own menu, which Plasma does not see as open).
    toolTipMainText: ""
    toolTipSubText: ""

    preferredRepresentation: compactRepresentation
    fullRepresentation: Item {}

    P5Support.DataSource {
        id: pmSource
        engine: "powermanagement"
        connectedSources: ["Battery", "AC Adapter"]
    }

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
        root.chargeLimit = 0;
        executable.connectSource(root.chargeLimitCommand);
        executable.connectSource(root.energyCommand);
        placePopover();
        popover.visible = true;
        popover.requestActivate();
    }

    // Under the item, kept inside the screen.
    function placePopover(): void {
        const anchor = root.compactRepresentationItem;
        if (!anchor) {
            return;
        }
        const origin = anchor.mapToGlobal(0, 0);
        const screen = Plasmoid.containment.screenGeometry;
        const width = popover.width > 0 ? popover.width : frame.width;
        let x = Math.round(origin.x + anchor.width / 2 - width / 2);
        x = Math.max(screen.x + popoverGap, Math.min(x, screen.x + screen.width - width - popoverGap));
        popover.x = x;
        popover.y = Math.round(origin.y + anchor.height + popoverGap) - glassPad;
    }

    compactRepresentation: MouseArea {
        id: compact

        Layout.minimumWidth: row.implicitWidth + Kirigami.Units.smallSpacing * 4
        Layout.preferredWidth: Layout.minimumWidth
        Layout.fillHeight: true
        hoverEnabled: true
        onClicked: root.togglePopover()

        // Highlighted only while open, never on hover, like macOS.
        Rectangle {
            anchors.centerIn: parent
            width: parent.width
            height: Kirigami.Units.iconSizes.smallMedium + Kirigami.Units.smallSpacing * 2
            radius: Kirigami.Units.cornerRadius
            color: Qt.rgba(0.5, 0.5, 0.5, 0.25)
            visible: popover.visible
        }

        Row {
            id: row
            anchors.centerIn: parent
            // On the clock's baseline (see the clock plasmoid).
            anchors.verticalCenterOffset: 1
            spacing: 6

            Text {
                anchors.verticalCenter: parent.verticalCenter
                text: Math.round(root.percent) + "%"
                // Pure white, like the other menu bar extras.
                color: "white"
                font: Kirigami.Theme.defaultFont
            }
            BatteryGlyph {
                anchors.verticalCenter: parent.verticalCenter
                anchors.verticalCenterOffset: -1
                percent: root.percent
                charging: root.charging || (root.pluggedIn && root.percent >= 100)
            }
        }
    }

    PlasmaCore.Dialog {
        id: popover

        location: PlasmaCore.Types.Floating
        backgroundHints: PlasmaCore.Dialog.NoBackground
        type: PlasmaCore.Dialog.PopupMenu
        flags: Qt.WindowStaysOnTopHint
        hideOnWindowDeactivate: true
        visible: false
        onVisibleChanged: {
            if (!visible) root.popoverHiddenAt = Date.now();
            else view.refresh();
        }

        mainItem: Item {
            width: frame.width
            height: frame.height + 2 * root.glassPad

            // One glass panel, like the Wi-Fi menu.
            Rectangle {
                id: frame

                readonly property bool dark: (0.299 * Kirigami.Theme.textColor.r + 0.587 * Kirigami.Theme.textColor.g
                                              + 0.114 * Kirigami.Theme.textColor.b) > 0.5
                readonly property real glassRadius: radius

                y: root.glassPad
                width: view.implicitWidth + 28
                height: view.implicitHeight + 24
                radius: 18
                // The Liquid Glass face (GlassSurface.qml); KWin blurs behind it.
                color: "transparent"

                GlassSurface {
                    anchors.fill: parent
                    z: -1
                    radius: frame.radius
                }

                BatteryView {
                    id: view
                    x: 14
                    y: 12
                    width: implicitWidth
                    height: implicitHeight
                    percent: root.percent
                    chargeLimit: root.chargeLimit
                    pluggedIn: root.pluggedIn
                    charging: root.charging
                    remainingMs: root.remainingMs
                    energyApplications: root.energyApplications
                    onCloseRequested: popover.visible = false
                    onRunCommand: command => executable.connectSource(command)
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

    // Measure again while the menu stays open, like macOS.
    Timer {
        interval: 5000
        repeat: true
        running: popover.visible
        onTriggered: {
            if (!executable.connectedSources.includes(root.energyCommand))
                executable.connectSource(root.energyCommand);
        }
    }

    P5Support.DataSource {
        id: executable
        engine: "executable"
        onNewData: (sourceName, data) => {
            if (sourceName === root.chargeLimitCommand) {
                const limits = String(data.stdout || "").trim().split(/\s+/)
                    .filter(value => /^\d+$/.test(value)).map(Number)
                    .filter(value => value > 0 && value <= 100);
                root.chargeLimit = limits.length && limits.every(value => value === limits[0]) ? limits[0] : 0;
            } else if (sourceName === root.energyCommand) {
                root.energyApplications = String(data.stdout || "").split("\n")
                    .map(line => line.split("\t")).filter(fields => fields.length === 3)
                    .map(fields => ({ name: fields[1], icon: fields[2] }));
            }
            disconnectSource(sourceName);
        }
    }
}
