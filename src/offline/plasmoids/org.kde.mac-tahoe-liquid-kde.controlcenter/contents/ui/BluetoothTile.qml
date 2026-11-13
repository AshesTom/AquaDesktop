/*
    MacTahoe Liquid KDE — the round Bluetooth toggle in the Tahoe Control Center.

    SPDX-License-Identifier: GPL-3.0-or-later
*/
import QtQuick

import org.kde.bluezqt as BluezQt
import org.kde.ki18n as KI18n

CircleButton {
    // Translations from this widget's catalog in any host: Plasma, or the
    // MacTahoe Liquid KDE shell (Quickshell has no KLocalizedContext).
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

    id: button
    glyph: "bluetooth"
    toolTip: i18nc("@action:button", "Bluetooth")
    enabled: BluezQt.Manager.adapters.length > 0
    active: BluezQt.Manager.bluetoothOperational

    // Match Plasma's Bluetooth applet: unblock rfkill, then power the
    // adapters; or block it all.
    onClicked: {
        const enable = !BluezQt.Manager.bluetoothOperational;
        BluezQt.Manager.bluetoothBlocked = !enable;
        for (const adapter of BluezQt.Manager.adapters) {
            adapter.powered = enable;
        }
    }
}
