/*
    AquaDesktop — the optional Plasma airplane-mode control. The Tahoe
    reference layout uses AirDrop at this position (AirDropTile.qml).

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

    id: button

    signal openSettings()

    glyph: "airplane"
    title: i18nc("@title Control Center module", "Airplane Mode")
    subtitle: active ? i18nc("@info Airplane Mode state", "On") : i18nc("@info Airplane Mode state", "Off")
    wrapTitle: true
    activeColor: "#ff9f0a"
    active: PlasmaNM.Configuration.airplaneModeEnabled
    onDetailsRequested: openSettings()

    onToggled: {
        const enable = !PlasmaNM.Configuration.airplaneModeEnabled;
        handler.enableAirplaneMode(enable);
        PlasmaNM.Configuration.airplaneModeEnabled = enable;
    }

    PlasmaNM.Handler {
        id: handler
    }
}
