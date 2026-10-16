/*
    AquaDesktop — Control Center Wi-Fi module (plasma-nm).

    SPDX-License-Identifier: GPL-3.0-or-later
*/
import QtQuick

import org.kde.plasma.networkmanagement as PlasmaNM
import org.kde.ki18n as KI18n

ToggleTile {
    // Translations from this widget's catalog in any host: Plasma, or the
    // AquaDesktop shell (Quickshell has no KLocalizedContext).
    KI18n.KI18nContext {
        id: widgetI18n
        translationDomain: "plasma_applet_org.kde.mac-tahoe-liquid-kde.controlcenter"
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

    id: tile

    signal openSettings()

    property string ssid: ""
    // Without Wi-Fi, the connection in use (macOS shows the wired one).
    property string otherConnection: ""

    glyph: "wifi"
    title: i18nc("@title Control Center module", "Wi-Fi")
    subtitle: !active ? i18nc("@info Wi-Fi state", "Off")
        : (ssid.length > 0 ? ssid
           : otherConnection.length > 0 ? otherConnection : i18nc("@info Wi-Fi state", "Not Connected"))
    active: enabledConnections.wirelessEnabled
    enabled: enabledConnections.wirelessHwEnabled

    onToggled: handler.enableWireless(!enabledConnections.wirelessEnabled)
    onDetailsRequested: openSettings()

    PlasmaNM.EnabledConnections {
        id: enabledConnections
    }

    PlasmaNM.Handler {
        id: handler
    }

    PlasmaNM.NetworkModel {
        id: networkModel
    }

    // The SSID of the activated wireless connection, if any.
    Instantiator {
        id: connections

        model: networkModel
        delegate: QtObject {
            required property var model
            readonly property string ssid: model.Ssid || ""
            readonly property string name: model.ItemUniqueName || ""
            readonly property bool activated: model.ConnectionState === PlasmaNM.Enums.Activated
            readonly property bool activeWifi: activated && ssid.length > 0
            readonly property bool activeOther: activated && model.Type === PlasmaNM.Enums.Wired
            onActiveWifiChanged: Qt.callLater(tile.refreshSsid)
            onActiveOtherChanged: Qt.callLater(tile.refreshSsid)
        }
        onObjectAdded: Qt.callLater(tile.refreshSsid)
        onObjectRemoved: Qt.callLater(tile.refreshSsid)
    }

    function refreshSsid(): void {
        let wifi = "", other = "";
        for (let i = 0; i < connections.count; ++i) {
            const connection = connections.objectAt(i);
            if (!connection) {
                continue;
            }
            if (connection.activeWifi && !wifi) {
                wifi = connection.ssid;
            } else if (connection.activeOther && !other) {
                other = connection.name;
            }
        }
        ssid = wifi;
        otherConnection = other;
    }
}
