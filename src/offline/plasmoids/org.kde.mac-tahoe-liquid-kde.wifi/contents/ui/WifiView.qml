/*
    AquaDesktop — the macOS Wi-Fi menu.

    Measured on a capture (1x): 16 px side padding (the dialog frame and
    this item), "Wi-Fi" in bold with the switch on the right, the current
    non-Wi-Fi connections ("Ethernet: Wired connection 1") as dimmed bold
    lines, then "Known Network" and "Other Networks" headings over their
    networks, a thin inset separator and "Wi-Fi Settings...". Rows are 22
    px apart; networks get 28 px rows with a 26 px round icon, filled with
    the accent colour while connected, and a lock when secured.

    This item uses no Plasmoid API, so it can also be rendered on its own.

    SPDX-License-Identifier: GPL-3.0-or-later
*/
import QtQuick
import QtQuick.Controls as QQC2
import QtQuick.Layouts

import org.kde.kcmutils as KCMUtils
import org.kde.kirigami as Kirigami
import org.kde.plasma.networkmanagement as PlasmaNM
import org.kde.ki18n as KI18n

Item {
    // Translations from this widget's catalog in any host: Plasma, or the
    // AquaDesktop shell (Quickshell has no KLocalizedContext).
    KI18n.KI18nContext {
        id: widgetI18n
        translationDomain: "plasma_applet_org.kde.mac-tahoe-liquid-kde.wifi"
    }
    function i18nc(context, text, arg1, arg2) {
        if (arg1 === undefined) {
            return widgetI18n.i18nc(context, text);
        }
        return arg2 === undefined ? widgetI18n.i18nc(context, text, arg1)
                                  : widgetI18n.i18nc(context, text, arg1, arg2);
    }
    function i18n(text, arg1) {
        return arg1 === undefined ? widgetI18n.i18n(text) : widgetI18n.i18n(text, arg1);
    }

    id: view

    // The accent itself, in Plasma as in Quickshell (see AccentColor.qml);
    // every child inherits it.
    AccentColor {
        id: kdeAccent
    }
    Binding {
        target: view.Kirigami.Theme
        property: "highlightColor"
        value: kdeAccent.value
        when: kdeAccent.valid
        restoreMode: Binding.RestoreBindingOrValue
    }

    signal closeRequested()

    readonly property bool wifiOn: enabledConnections.wirelessEnabled
    readonly property bool wifiHardware: availableDevices.wirelessDeviceAvailable
        && enabledConnections.wirelessHwEnabled
    // Snapshots of the network model, rebuilt when it changes (see below).
    property var known: []
    property var others: []
    property var current: []
    property string connectedNetwork: ""
    readonly property string currentSummary: connectedNetwork.length > 0 ? connectedNetwork
        : current.length > 0 ? current[0].label : i18nc("@info Wi-Fi state", "Not Connected")

    readonly property int textSize: 13
    readonly property color dimmed: Qt.rgba(Kirigami.Theme.textColor.r, Kirigami.Theme.textColor.g,
                                            Kirigami.Theme.textColor.b, 0.55)

    // macOS Tahoe's Wi-Fi menu: 310 px wide with its 14 px padding.
    implicitWidth: 282
    // Other Networks stay folded behind their row, as on macOS.
    property bool othersOpen: false
    implicitHeight: column.implicitHeight

    PlasmaNM.EnabledConnections {
        id: enabledConnections
    }

    PlasmaNM.AvailableDevices {
        id: availableDevices
    }

    PlasmaNM.Handler {
        id: handler
    }

    PlasmaNM.NetworkModel {
        id: networkModel
    }

    PlasmaNM.AppletProxyModel {
        id: proxyModel
        sourceModel: networkModel
    }

    Instantiator {
        id: entries

        model: proxyModel
        delegate: QtObject {
            required property var model
            readonly property string name: model.ItemUniqueName || ""
            readonly property int type: model.Type
            readonly property int state: model.ConnectionState
            readonly property string uuid: model.Uuid || ""
            readonly property int security: model.SecurityType
            readonly property string icon: model.ConnectionIcon || ""
            readonly property string connectionPath: model.ConnectionPath || ""
            readonly property string devicePath: model.DevicePath || ""
            readonly property string specificPath: model.SpecificPath || ""
            readonly property bool duplicate: !!model.Duplicate
            onNameChanged: Qt.callLater(view.rebuild)
            onStateChanged: Qt.callLater(view.rebuild)
            onUuidChanged: Qt.callLater(view.rebuild)
            onIconChanged: Qt.callLater(view.rebuild)
        }
        onObjectAdded: Qt.callLater(view.rebuild)
        onObjectRemoved: Qt.callLater(view.rebuild)
    }

    function typeName(type: int): string {
        switch (type) {
        case PlasmaNM.Enums.Wired: return i18nc("@info connection type", "Ethernet");
        case PlasmaNM.Enums.Vpn: return i18nc("@info connection type", "VPN");
        case PlasmaNM.Enums.Bluetooth: return i18nc("@info connection type", "Bluetooth");
        case PlasmaNM.Enums.Gsm: return i18nc("@info connection type", "Mobile");
        default: return "";
        }
    }

    function rebuild(): void {
        const known = [], others = [], current = [];
        for (let i = 0; i < entries.count; ++i) {
            const entry = entries.objectAt(i);
            if (!entry || entry.duplicate) {
                continue;
            }
            const active = entry.state === PlasmaNM.Enums.Activated
                || entry.state === PlasmaNM.Enums.Activating;
            const item = {
                name: entry.name, uuid: entry.uuid, icon: entry.icon,
                security: entry.security, active: active,
                connecting: entry.state === PlasmaNM.Enums.Activating,
                connectionPath: entry.connectionPath, devicePath: entry.devicePath,
                specificPath: entry.specificPath,
            };
            if (entry.type === PlasmaNM.Enums.Wireless) {
                (entry.uuid.length > 0 ? known : others).push(item);
            } else if (active && typeName(entry.type).length > 0) {
                item.label = typeName(entry.type) + ": " + entry.name;
                current.push(item);
            }
        }
        // Connected networks first, as macOS lists them.
        known.sort((a, b) => (b.active ? 1 : 0) - (a.active ? 1 : 0));
        const connected = known.concat(others).find(network => network.active);
        view.connectedNetwork = connected ? connected.name : "";
        view.known = known;
        view.others = others;
        // Only the other kinds of connection get a line of their own.
        view.current = current;
    }

    // Saved networks and open ones connect at once; a secured new one asks
    // for its password in its row first.
    function activate(network: var, password: string): void {
        if (network.active) {
            handler.deactivateConnection(network.connectionPath, network.devicePath);
        } else if (network.uuid.length > 0) {
            handler.activateConnection(network.connectionPath, network.devicePath, network.specificPath);
        } else {
            handler.addAndActivateConnection(network.devicePath, network.specificPath, password);
        }
    }

    function needsPassword(network: var): bool {
        return network.uuid.length === 0 && network.security !== PlasmaNM.Enums.NoneSecurity;
    }

    ColumnLayout {
        id: column

        width: parent.width
        spacing: 0

        // Wi-Fi and its switch.
        RowLayout {
            Layout.fillWidth: true
            Layout.preferredHeight: 30
            Layout.leftMargin: 2
            Layout.rightMargin: 2

            Text {
                Layout.fillWidth: true
                text: i18nc("@title", "Wi-Fi")
                color: Kirigami.Theme.textColor
                font.weight: Font.Bold
                font.pixelSize: view.textSize
            }
            MacSwitch {
                checked: view.wifiOn
                enabled: enabledConnections.wirelessHwEnabled
                onToggled: handler.enableWireless(!view.wifiOn)
            }
        }
        Separator {}

        // The current connections.
        Repeater {
            model: view.current
            delegate: Text {
                required property var modelData
                Layout.fillWidth: true
                Layout.preferredHeight: 22
                Layout.leftMargin: 2
                verticalAlignment: Text.AlignVCenter
                text: modelData.label
                color: view.dimmed
                font.weight: Font.DemiBold
                font.pixelSize: view.textSize - 1
                elide: Text.ElideRight
            }
        }

        Heading {
            text: i18nc("@title Wi-Fi menu section", "Known Networks")
            visible: view.wifiOn && view.known.length > 0
        }
        Repeater {
            model: view.wifiOn ? view.known : []
            delegate: NetworkRow {
                required property var modelData
                network: modelData
            }
        }

        // Other Networks: a row folding the list open, with its chevron.
        Separator {
            visible: view.wifiOn
        }
        Rectangle {
            id: othersRow
            Layout.fillWidth: true
            Layout.leftMargin: -8
            Layout.rightMargin: -8
            Layout.preferredHeight: 28
            visible: view.wifiOn
            radius: 10
            color: othersArea.containsMouse
                ? Qt.rgba(Kirigami.Theme.textColor.r, Kirigami.Theme.textColor.g, Kirigami.Theme.textColor.b, 0.10)
                : "transparent"
            Text {
                x: 10
                anchors.verticalCenter: parent.verticalCenter
                text: i18nc("@title Wi-Fi menu section", "Other Networks")
                color: view.dimmed
                font.weight: Font.Bold
                font.pixelSize: view.textSize - 1
            }
            // The chevron: right while folded, down when open.
            Text {
                anchors.right: parent.right
                anchors.rightMargin: 12
                anchors.verticalCenter: parent.verticalCenter
                text: "›"
                rotation: view.othersOpen ? 90 : 0
                color: view.dimmed
                font.pixelSize: 18
                Behavior on rotation {
                    NumberAnimation { duration: Kirigami.Units.shortDuration }
                }
            }
            MouseArea {
                id: othersArea
                anchors.fill: parent
                hoverEnabled: true
                onClicked: view.othersOpen = !view.othersOpen
            }
        }
        Repeater {
            model: view.wifiOn && view.othersOpen ? view.others : []
            delegate: NetworkRow {
                required property var modelData
                network: modelData
            }
        }
        Text {
            Layout.fillWidth: true
            Layout.preferredHeight: 22
            Layout.leftMargin: 2
            visible: view.wifiOn && view.othersOpen && view.others.length === 0
            verticalAlignment: Text.AlignVCenter
            text: view.wifiHardware ? i18nc("@info", "No networks found")
                : i18nc("@info", "No Wi-Fi hardware or service (NetworkManager)")
            color: Qt.rgba(view.dimmed.r, view.dimmed.g, view.dimmed.b, 0.4)
            font.pixelSize: view.textSize - 1
            elide: Text.ElideRight
        }

        Separator {}

        MenuRow {
            text: i18nc("@action:button", "Wi-Fi Settings…")
            onClicked: {
                view.closeRequested();
                KCMUtils.KCMLauncher.openSystemSettings("kcm_networkmanagement");
            }
        }
    }

    // A hairline between the menu's sections.
    component Separator: Rectangle {
        Layout.fillWidth: true
        Layout.topMargin: 6
        Layout.bottomMargin: 6
        Layout.preferredHeight: 1
        color: Qt.rgba(Kirigami.Theme.textColor.r, Kirigami.Theme.textColor.g,
                       Kirigami.Theme.textColor.b, 0.15)
    }

    component Heading: Text {
        Layout.fillWidth: true
        Layout.preferredHeight: 22
        Layout.leftMargin: 2
        verticalAlignment: Text.AlignVCenter
        color: view.dimmed
        font.weight: Font.Bold
        font.pixelSize: view.textSize - 1
    }

    // A menu entry: highlighted with the accent colour under the pointer.
    component MenuRow: Rectangle {
        id: menuRow

        property alias text: label.text
        signal clicked()

        Layout.fillWidth: true
        Layout.leftMargin: -8
        Layout.rightMargin: -8
        Layout.preferredHeight: 26
        radius: 10
        color: area.containsMouse ? Kirigami.Theme.highlightColor : "transparent"

        Text {
            id: label
            anchors {
                left: parent.left
                leftMargin: 10
                verticalCenter: parent.verticalCenter
            }
            color: area.containsMouse ? Kirigami.Theme.highlightedTextColor : Kirigami.Theme.textColor
            font.pixelSize: view.textSize
        }
        MouseArea {
            id: area
            anchors.fill: parent
            hoverEnabled: true
            onClicked: menuRow.clicked()
        }
    }

    component NetworkRow: Rectangle {
        id: networkRow

        property var network
        property bool askingPassword: false

        Layout.fillWidth: true
        Layout.leftMargin: -8
        Layout.rightMargin: -8
        Layout.preferredHeight: askingPassword ? 64 : 32
        radius: 10
        color: rowArea.containsMouse && !askingPassword
            ? Qt.rgba(Kirigami.Theme.textColor.r, Kirigami.Theme.textColor.g, Kirigami.Theme.textColor.b, 0.10)
            : "transparent"

        Rectangle {
            id: disc
            x: 10
            y: 3
            width: 26
            height: 26
            radius: 13
            color: networkRow.network.active ? Kirigami.Theme.highlightColor
                : Qt.rgba(Kirigami.Theme.textColor.r, Kirigami.Theme.textColor.g, Kirigami.Theme.textColor.b, 0.16)
            opacity: networkRow.network.connecting ? 0.6 : 1

            Glyph {
                anchors.centerIn: parent
                anchors.verticalCenterOffset: -1
                width: 15
                height: 15
                glyph: "wifi"
                color: networkRow.network.active ? Kirigami.Theme.highlightedTextColor : Kirigami.Theme.textColor
            }
        }

        Text {
            anchors {
                left: disc.right
                leftMargin: 8
                right: lock.left
                rightMargin: 6
                verticalCenter: disc.verticalCenter
            }
            text: networkRow.network.name
            color: Kirigami.Theme.textColor
            font.pixelSize: view.textSize
            elide: Text.ElideRight
        }

        Glyph {
            id: lock
            anchors {
                right: parent.right
                rightMargin: 14
                verticalCenter: disc.verticalCenter
            }
            width: 12
            height: 12
            glyph: "lock"
            color: view.dimmed
            visible: networkRow.network.security !== PlasmaNM.Enums.NoneSecurity
        }

        MouseArea {
            id: rowArea
            width: parent.width
            height: 32
            hoverEnabled: true
            onClicked: {
                if (view.needsPassword(networkRow.network) && !networkRow.network.active) {
                    networkRow.askingPassword = !networkRow.askingPassword;
                    if (networkRow.askingPassword) {
                        password.forceActiveFocus();
                    }
                } else {
                    view.activate(networkRow.network, "");
                }
            }
        }

        QQC2.TextField {
            id: password
            anchors {
                left: parent.left
                leftMargin: disc.width + 10
                right: parent.right
                rightMargin: 6
                bottom: parent.bottom
                bottomMargin: 2
            }
            visible: networkRow.askingPassword
            echoMode: TextInput.Password
            placeholderText: i18nc("@info:placeholder", "Password")
            onAccepted: {
                view.activate(networkRow.network, text);
                networkRow.askingPassword = false;
                text = "";
            }
            Keys.onEscapePressed: networkRow.askingPassword = false
        }
    }

    // The macOS Tahoe switch: a 50 x 24 accent pill, a 30 x 20 white capsule.
    component MacSwitch: Item {
        id: macSwitch

        property bool checked: false
        signal toggled()

        implicitWidth: 50
        implicitHeight: 24
        opacity: enabled ? 1 : 0.4

        Rectangle {
            anchors.fill: parent
            radius: height / 2
            color: macSwitch.checked ? Kirigami.Theme.highlightColor
                : Qt.rgba(Kirigami.Theme.textColor.r, Kirigami.Theme.textColor.g, Kirigami.Theme.textColor.b, 0.22)
            Behavior on color {
                ColorAnimation { duration: Kirigami.Units.shortDuration }
            }
        }
        Rectangle {
            width: 30
            height: 20
            radius: 10
            y: 2
            x: macSwitch.checked ? parent.width - width - 2 : 2
            color: "white"
            Behavior on x {
                NumberAnimation { duration: Kirigami.Units.shortDuration; easing.type: Easing.OutCubic }
            }
        }
        MouseArea {
            anchors.fill: parent
            onClicked: macSwitch.toggled()
        }
    }
}
